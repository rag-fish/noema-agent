#!/usr/bin/env bash
# noema-agent UAT runner
#
# Usage:
#   ./uat/uat.sh                     # run all scenarios against localhost:8000
#   ./uat/uat.sh --port 8001         # custom port (e.g. agent-dev)
#   ./uat/uat.sh --scenarios uat/scenarios/epic2.yaml
#   ./uat/uat.sh --no-docker         # skip Docker startup check
#
# Requirements:
#   - Docker (unless --no-docker)
#   - Python 3.11+
#   - ANTHROPIC_API_KEY in environment
#   - pip install -r uat/requirements-uat.txt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ────────────────────────────────────────────────────────────────
PORT=8000
SCENARIOS_DIR="$SCRIPT_DIR/scenarios"
SCENARIOS_FILE=""  # empty = run all .yaml in SCENARIOS_DIR
SKIP_DOCKER=false
COMPOSE_SERVICE="agent"

# ── Colours ─────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[UAT]${NC} $*"; }
ok()    { echo -e "${GREEN}[PASS]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

# ── Argument parsing ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)       PORT="$2";       shift 2 ;;
        --scenarios)  SCENARIOS_FILE="$2"; shift 2 ;;
        --no-docker)  SKIP_DOCKER=true; shift ;;
        --dev)        PORT=8001; COMPOSE_SERVICE="agent-dev"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

BASE_URL="http://localhost:${PORT}"

# ── Pre-flight: ANTHROPIC_API_KEY ───────────────────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    fail "ANTHROPIC_API_KEY is not set. Claude judge will not work."
    echo "  export ANTHROPIC_API_KEY=sk-..."
    exit 1
fi

# ── Pre-flight: Python ─────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    fail "python3 not found"
    exit 1
fi

# ── Docker startup ───────────────────────────────────────────────────────────
if [[ "$SKIP_DOCKER" == false ]]; then
    info "Starting Docker service: ${COMPOSE_SERVICE} ..."
    cd "$REPO_ROOT"
    docker compose up -d "$COMPOSE_SERVICE"

    # Wait for health check (max 30s)
    info "Waiting for agent to be healthy ..."
    RETRIES=0
    until curl -sf "${BASE_URL}/health" > /dev/null 2>&1; do
        RETRIES=$((RETRIES + 1))
        if [[ $RETRIES -ge 30 ]]; then
            fail "Agent did not become healthy within 30s"
            docker compose logs "$COMPOSE_SERVICE" | tail -20
            exit 1
        fi
        sleep 1
    done
    ok "Agent is healthy at ${BASE_URL}"
else
    info "--no-docker: skipping Docker startup"
    if ! curl -sf "${BASE_URL}/health" > /dev/null 2>&1; then
        fail "Agent not reachable at ${BASE_URL}/health"
        exit 1
    fi
    ok "Agent reachable at ${BASE_URL}"
fi

# ── Run UAT scenarios via Python runner ────────────────────────────────────────
echo
info "Running UAT scenarios ..."
echo

PYTHON_ARGS=("$SCRIPT_DIR/runner.py" "--base-url" "$BASE_URL")

if [[ -n "$SCENARIOS_FILE" ]]; then
    PYTHON_ARGS+=("--scenarios" "$SCENARIOS_FILE")
else
    PYTHON_ARGS+=("--scenarios-dir" "$SCENARIOS_DIR")
fi

python3 "${PYTHON_ARGS[@]}"
EXIT_CODE=$?

echo
if [[ $EXIT_CODE -eq 0 ]]; then
    ok "${BOLD}All UAT scenarios passed."
else
    fail "${BOLD}One or more UAT scenarios failed."
fi

exit $EXIT_CODE
