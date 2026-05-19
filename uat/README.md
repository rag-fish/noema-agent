# noema-agent UAT Tool

Semi-automated UAT runner for local acceptance testing of noema-agent.

Architecture:
- `uat.sh` — entry point: Docker startup + health check + Python runner invocation
- `runner.py` — loads YAML scenarios, calls `/invoke`, judges responses via Claude API
- `scenarios/` — YAML scenario files (one per EPIC or feature area)

## Design note: LLM-as-judge

noema-agent enforces structural constraints so LLMs don’t need to decide what to block.
The UAT tool inverts this: it uses Claude to judge whether responses are *correct*,
because “is this response appropriate?” is exactly the kind of judgement LLMs handle well.
Constraint system judged by a free-ranging LLM — intentionally ironic.

## Prerequisites

```bash
# 1. Docker (for agent startup)
# 2. Python 3.11+
# 3. UAT deps
pip install -r uat/requirements-uat.txt

# 4. API key
export ANTHROPIC_API_KEY=sk-...
```

## Usage

```bash
# All scenarios, auto-start Docker (prod, port 8000)
./uat/uat.sh

# Dev container (port 8001)
./uat/uat.sh --dev

# Single scenario file
./uat/uat.sh --scenarios uat/scenarios/epic2_constraint_engine.yaml

# Agent already running (skip Docker)
./uat/uat.sh --no-docker

# Custom port
./uat/uat.sh --port 8002
```

## Adding scenarios

Create a new `.yaml` file in `uat/scenarios/`:

```yaml
scenarios:
  - name: my_scenario
    description: What this tests
    request:
      task_type: echo
      payload:
        message: hello
      privacy_level: local   # optional
    expectation: >
      Describe what a correct response looks like.
      Claude will judge actual vs expected.
```

No code changes needed. The runner picks up all `*.yaml` files automatically.

## Output example

```
[UAT] Starting Docker service: agent ...
[PASS] Agent is healthy at http://localhost:8000

============================================================
Scenario file: epic2_constraint_engine.yaml
============================================================
  echo_basic
  Normal echo request should succeed
  PASS — Response returned status=success with payload echoed correctly.

  oversized_payload_rejected
  Payload exceeding 64KB should be rejected with E-EXEC-005
  PASS — Response correctly returned status=error with error.code=E-EXEC-005.

  unsupported_task_type
  Unknown task type should return E-EXEC-001
  PASS — Non-recoverable E-EXEC-001 returned as expected.

============================================================
Results: 6 passed, 0 failed, 6 total
============================================================
```
