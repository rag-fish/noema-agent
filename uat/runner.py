"""
noema-agent UAT runner

Loads scenario YAML files, calls /invoke on the running agent,
then asks Claude to judge each response against the scenario's expectation.

Claude returns structured JSON: { "pass": bool, "reason": str }
This is the "ironical" core: a constraint-enforcement agent judged by an LLM.

Usage (called by uat.sh, or directly):
    python3 uat/runner.py --base-url http://localhost:8000
    python3 uat/runner.py --base-url http://localhost:8000 --scenarios uat/scenarios/epic2.yaml
    python3 uat/runner.py --base-url http://localhost:8000 --scenarios-dir uat/scenarios/
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import requests
import yaml

# ANSI colours
GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
NC     = "\033[0m"


def _c(colour: str, text: str) -> str:
    return f"{colour}{text}{NC}"


# ---------------------------------------------------------------------------
# Claude judge
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = (
    "You are a UAT judge for noema-agent, a constrained execution API.\n"
    "You receive a test scenario description, the HTTP request sent, and the HTTP response received.\n"
    "Your job: decide whether the response matches the scenario's expectation.\n"
    "\n"
    "Respond ONLY with a JSON object. No markdown, no preamble.\n"
    'Schema: { \"pass\": true | false, \"reason\": \"one concise sentence\" }\n'
    "\n"
    "Judgement guidelines:\n"
    "- Focus on whether the response behaviour matches the stated expectation.\n"
    "- For error scenarios: check status, error code, and that no unintended data leaked.\n"
    "- For success scenarios: check status=success and result content.\n"
    "- If the response is structurally malformed (not valid JSON), always fail.\n"
    "- Be strict about error codes (E-EXEC-001, E-EXEC-004, E-EXEC-005, etc.).\n"
    "- Do NOT penalise for fields not mentioned in the expectation."
)


def judge_with_claude(
    scenario_name: str,
    expectation: str,
    request_body: dict,
    response_body: dict,
    response_status: int,
) -> dict:
    """
    Ask Claude to judge whether the response satisfies the scenario expectation.
    Returns { "pass": bool, "reason": str }
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"pass": False, "reason": "ANTHROPIC_API_KEY not set"}

    # Truncate request body for judge (avoid sending huge payloads to Claude)
    request_summary = json.dumps(request_body, ensure_ascii=False)
    if len(request_summary) > 2000:
        request_summary = request_summary[:2000] + "... [truncated]"

    user_message = (
        f"Scenario: {scenario_name}\n\n"
        f"Expectation:\n{expectation}\n\n"
        f"HTTP request body sent to /invoke:\n{request_summary}\n\n"
        f"HTTP response status: {response_status}\n"
        f"HTTP response body:\n{json.dumps(response_body, indent=2, ensure_ascii=False)}\n\n"
        "Does this response satisfy the expectation?"
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",  # current model string
                "max_tokens": 256,
                "system": JUDGE_SYSTEM,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"].strip()
        # Strip markdown fences if model wraps response
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except requests.HTTPError as exc:
        body = ""
        try:
            body = exc.response.json().get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            pass
        return {"pass": False, "reason": f"Claude API error {exc.response.status_code}: {body or exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"pass": False, "reason": f"Judge error: {exc}"}


# ---------------------------------------------------------------------------
# Scenario loader
# ---------------------------------------------------------------------------

def load_scenarios(path: Path) -> list[dict]:
    """
    Load one YAML file. Expected structure:

    scenarios:
      - name: ...
        description: ...
        request:
          task_type: echo
          payload: { ... }
          privacy_level: local      # optional
        expectation: >
          The agent should return status=success and echo the payload unchanged.
    """
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("scenarios", [])


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

def run_scenario(scenario: dict, base_url: str) -> bool:
    """
    Execute one scenario: call /invoke, judge with Claude, print result.
    Returns True if passed.
    """
    name        = scenario.get("name", "unnamed")
    description = scenario.get("description", "")
    expectation = scenario.get("expectation", "")
    req_spec    = scenario.get("request", {})

    print(f"  {_c(BOLD, name)}")
    if description:
        print(f"  {_c(CYAN, description)}")

    # Build request body
    # payload_override allows scenarios to specify a generated payload
    raw_payload = req_spec.get("payload", {})
    payload_size = req_spec.get("payload_size_bytes", None)
    if payload_size:
        # Generate a payload of exactly the requested byte size
        filler = "X" * payload_size
        raw_payload = {"data": filler}

    request_body: dict[str, Any] = {
        "session_id": f"uat-{uuid.uuid4()}",
        "request_id": str(uuid.uuid4()),
        "task_type":  req_spec.get("task_type", "echo"),
        "payload":    raw_payload,
    }
    if "privacy_level" in req_spec:
        request_body["privacy_level"] = req_spec["privacy_level"]

    # Call the agent
    try:
        http_resp = requests.post(
            f"{base_url}/invoke",
            json=request_body,
            timeout=10,
        )
        response_status = http_resp.status_code
        try:
            response_body = http_resp.json()
        except Exception:  # noqa: BLE001
            response_body = {"raw": http_resp.text}
    except requests.RequestException as exc:
        print(f"  {_c(RED, 'NETWORK ERROR')}: {exc}")
        return False

    # Judge with Claude
    judgment = judge_with_claude(
        scenario_name=name,
        expectation=expectation,
        request_body=request_body,
        response_body=response_body,
        response_status=response_status,
    )

    passed = bool(judgment.get("pass", False))
    reason = judgment.get("reason", "(no reason)")

    if passed:
        print(f"  {_c(GREEN, 'PASS')} \u2014 {reason}")
    else:
        print(f"  {_c(RED, 'FAIL')} \u2014 {reason}")
        print(f"  response status : {response_status}")
        print(f"  response excerpt: {json.dumps(response_body)[:300]}")

    print()
    return passed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="noema-agent UAT runner")
    parser.add_argument("--base-url",      default="http://localhost:8000")
    parser.add_argument("--scenarios",     help="Single scenario YAML file")
    parser.add_argument("--scenarios-dir", help="Directory of scenario YAML files")
    args = parser.parse_args()

    # Collect scenario files
    scenario_files: list[Path] = []
    if args.scenarios:
        scenario_files = [Path(args.scenarios)]
    elif args.scenarios_dir:
        scenario_files = sorted(Path(args.scenarios_dir).glob("*.yaml"))
    else:
        default_dir = Path(__file__).parent / "scenarios"
        scenario_files = sorted(default_dir.glob("*.yaml"))

    if not scenario_files:
        print(_c(YELLOW, "[WARN] No scenario files found."))
        return 0

    total  = 0
    passed = 0

    for yaml_path in scenario_files:
        print(_c(BOLD, f"\n{'='*60}"))
        print(_c(BOLD, f"Scenario file: {yaml_path.name}"))
        print(_c(BOLD, f"{'='*60}"))

        scenarios = load_scenarios(yaml_path)
        for scenario in scenarios:
            total += 1
            if run_scenario(scenario, args.base_url):
                passed += 1

    # Summary
    failed = total - passed
    print(_c(BOLD, f"{'='*60}"))
    print(f"Results: {_c(GREEN, str(passed))} passed, {_c(RED, str(failed))} failed, {total} total")
    print(_c(BOLD, f"{'='*60}"))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
