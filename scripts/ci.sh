#!/bin/bash
# Root CI Script — cross-project checks only
# Domain checks live in backend/scripts/ci/ci.sh and frontend/scripts/ci/ci.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
FAILED=0

log_info()  { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}❌${NC} $1"; }
log_warn()  { echo -e "${YELLOW}⚠️${NC} $1"; }
log_section() { echo -e "\n${BLUE}=== $1 ===${NC}"; }

check_command() {
    if ! command -v "$1" &>/dev/null; then
        log_error "$1 is not installed"
        return 1
    fi
    return 0
}

# ── openapi ──────────────────────────────────────────────────────────────────

run_openapi() {
    log_section "OpenAPI Drift Check"

    # Step 1: Backend — export spec and validate it matches committed openapi.json
    log_info "Exporting backend OpenAPI spec..."
    cd "$REPO_ROOT/backend"
    check_command uv || return 1

    export FEISHU__PLATFORM__APP_ID="${FEISHU__PLATFORM__APP_ID:-ci_dummy}"
    export FEISHU__PLATFORM__APP_SECRET="${FEISHU__PLATFORM__APP_SECRET:-ci_dummy}"
    export FEISHU__PLATFORM__REDIRECT_URI="${FEISHU__PLATFORM__REDIRECT_URI:-http://localhost:3000/callback}"
    export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

    uv run python scripts/ci/export_openapi.py
    if ! git diff --exit-code openapi.json > /dev/null 2>&1; then
        log_error "Backend OpenAPI spec is out of date! Run 'uv run python scripts/ci/export_openapi.py' and commit."
        FAILED=1
        return 1
    fi
    log_info "Backend OpenAPI spec is up to date"

    # Step 2: Frontend — generate types from spec and check drift
    cd "$REPO_ROOT/frontend"
    check_command pnpm || return 1

    BACKEND_SPEC="$REPO_ROOT/backend/openapi.json"
    if [ ! -f "$BACKEND_SPEC" ]; then
        log_error "Backend openapi.json not found at $BACKEND_SPEC"
        FAILED=1
        return 1
    fi
    cp "$BACKEND_SPEC" src/types/generated/openapi.json
    if ! BACKEND_SPEC_PATH=src/types/generated/openapi.json pnpm generate:api; then
        log_error "Failed to generate API types"
        FAILED=1
        return 1
    fi
    if ! git diff --exit-code src/types/generated/schema.ts > /dev/null 2>&1; then
        log_error "Generated types are out of date!"
        echo ""
        echo "The backend API has changed. Please update the frontend types:"
        echo "  1. Pull the latest backend changes"
        echo "  2. Run: bash scripts/ci.sh openapi"
        echo "  3. Commit the updated src/types/generated/schema.ts"
        FAILED=1
    else
        log_info "Generated types are up to date"
    fi

    cd "$REPO_ROOT"
}

# ── e2e ──────────────────────────────────────────────────────────────────────

run_e2e() {
    log_section "E2E Tests"
    cd "$REPO_ROOT"

    # ── Cleanup trap ────────────────────────────────────────────────────
    cleanup() {
        docker compose -p dazah-e2e -f docker-compose.e2e.yml down -v --remove-orphans 2>/dev/null || true
    }
    trap cleanup EXIT

    # ── Start E2E services ──────────────────────────────────────────────
    log_info "Starting E2E services (postgres + backend + frontend)..."
    docker compose -p dazah-e2e -f docker-compose.e2e.yml up -d --build

    # ── Wait for backend ────────────────────────────────────────────────
    backend_ready=false
    for _ in $(seq 1 60); do
        if curl -sf http://127.0.0.1:18000/health > /dev/null 2>&1; then
            backend_ready=true
            break
        fi
        sleep 2
    done
    if [[ "$backend_ready" != true ]]; then
        log_error "Backend did not become ready"
        exit 1
    fi
    log_info "Backend ready"

    # ── Wait for frontend ───────────────────────────────────────────────
    frontend_ready=false
    for _ in $(seq 1 30); do
        if curl -sf http://127.0.0.1:13000 > /dev/null 2>&1; then
            frontend_ready=true
            break
        fi
        sleep 2
    done
    if [[ "$frontend_ready" != true ]]; then
        log_error "Frontend did not become ready"
        exit 1
    fi
    log_info "Frontend ready"

    # ── Run Playwright ──────────────────────────────────────────────────
    export E2E_BACKEND_URL="http://127.0.0.1:18000"
    export E2E_FRONTEND_URL="http://127.0.0.1:13000"
    export E2E_AUTH_SECRET="e2e-test-secret"

    log_info "Running Playwright tests..."
    cd "$REPO_ROOT/frontend"
    if ! pnpm exec playwright test; then
        log_error "E2E tests failed!"
        FAILED=1
    else
        log_info "E2E tests passed"
    fi

    cd "$REPO_ROOT"
}

# ── Help ─────────────────────────────────────────────────────────────────────

show_help() {
    echo "Usage: $0 [openapi|e2e]"
    echo ""
    echo "Cross-project CI checks:"
    echo "  openapi  — Backend spec export + frontend type generation + drift check"
    echo "  e2e      — Start services + run Playwright end-to-end tests"
    echo ""
    echo "Domain checks:"
    echo "  cd backend && bash scripts/ci/ci.sh lint|typecheck|alembic|test|migration-scope"
    echo "  cd frontend && bash scripts/ci/ci.sh lint|typecheck|build"
}

# ── Dispatch ─────────────────────────────────────────────────────────────────

SUBCOMMANDS=()
for arg in "$@"; do
    case "$arg" in
        --help|-h) show_help; exit 0 ;;
        -*) echo "Unknown option: $arg"; exit 1 ;;
        *) SUBCOMMANDS+=("$arg") ;;
    esac
done

if [ ${#SUBCOMMANDS[@]} -eq 0 ]; then
    show_help
    exit 1
fi

for cmd in "${SUBCOMMANDS[@]}"; do
    case "${cmd}" in
        openapi) run_openapi ;;
        e2e)     run_e2e ;;
        *)
            echo "Unknown subcommand: ${cmd}"
            show_help
            exit 1
            ;;
    esac
done

echo ""
if [ $FAILED -eq 0 ]; then
    log_info "All checks passed!"
    exit 0
else
    log_error "Some checks failed!"
    exit 1
fi
