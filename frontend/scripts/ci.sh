#!/bin/bash
# Frontend CI Script - Single source of truth for all checks
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
FAILED=0

log_info() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}❌${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
log_section() { echo -e "\n${BLUE}=== $1 ===${NC}"; }

check_node_version() {
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"; return 1
    fi
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 22 ]; then
        log_warn "Node.js version is $(node -v), but CI uses Node.js 22"
    fi
    return 0
}

clean_next() {
    log_section "Cleaning .next Directory"
    if [ -d ".next" ]; then
        rm -rf .next
        test ! -e .next || { log_error "Cannot remove .next directory (check ownership: ls -la .next)"; exit 1; }
        log_info "Removed .next directory"
    else
        log_info ".next directory does not exist"
    fi
}

install_deps() {
    log_section "Installing Dependencies"
    if ! command -v pnpm &> /dev/null; then
        log_error "pnpm is not installed. Install with: npm install -g pnpm"
        FAILED=1; return 1
    fi
    if [ "$CI" = "true" ]; then
        if ! pnpm install --frozen-lockfile; then
            log_error "Failed to install dependencies with --frozen-lockfile"
            FAILED=1; return 1
        fi
    else
        if ! pnpm install; then
            log_error "Failed to install dependencies"
            FAILED=1; return 1
        fi
    fi
    log_info "Dependencies installed"
}

run_typecheck() {
    log_section "TypeScript Check"
    check_node_version || return 1
    install_deps || return 1
    if ! pnpm typecheck; then
        log_error "TypeScript check failed!"; FAILED=1
    else
        log_info "TypeScript check passed"
    fi
}

run_lint() {
    log_section "ESLint"
    check_node_version || return 1
    install_deps || return 1
    if ! pnpm lint; then
        log_error "Linter failed!"; FAILED=1
    else
        log_info "Linter passed"
    fi
}

run_build() {
    log_section "Next.js Build (Docker)"
    ROOT_DIR="$(cd "$PROJECT_ROOT/.." && pwd)"
    if ! docker compose -f "$ROOT_DIR/docker-compose.yml" -f "$ROOT_DIR/docker-compose.dev.yml" run --rm --build frontend sh -c "pnpm build"; then
        log_error "Build failed!"; FAILED=1
    else
        log_info "Build passed"
    fi
}

run_openapi() {
    log_section "OpenAPI Drift Check"
    check_node_version || return 1
    install_deps || return 1
    BACKEND_REPO="${BACKEND_REPO_PATH:-../backend}"
    BACKEND_SPEC="$BACKEND_REPO/openapi.json"
    if [ ! -f "$BACKEND_SPEC" ]; then
        log_warn "Backend openapi.json not found at $BACKEND_SPEC"
        log_warn "Skipping OpenAPI drift check"
        return 0
    fi
    cp "$BACKEND_SPEC" src/types/generated/openapi.json
    if ! BACKEND_SPEC_PATH=src/types/generated/openapi.json pnpm generate:api; then
        log_error "Failed to generate API types"; FAILED=1; return 1
    fi
    if ! git diff --exit-code src/types/generated/schema.ts > /dev/null 2>&1; then
        log_error "Generated types are out of date!"
        echo ""
        echo "The backend API has changed. Please update the frontend types:"
        echo "  1. Pull the latest backend changes"
        echo "  2. Run: pnpm generate:api"
        echo "  3. Commit the updated src/types/generated/schema.ts"
        FAILED=1
    else
        log_info "Generated types are up to date"
    fi
}

run_e2e() {
    log_section "E2E Tests"
    check_node_version || return 1
    install_deps || return 1
    if ! npx playwright --version 2>/dev/null; then
        log_warn "Playwright not configured (run 'pnpm exec playwright install chromium' first)"
        return 0
    fi
    if ! pnpm test:e2e; then
        log_error "E2E tests failed!"; FAILED=1
    else
        log_info "E2E tests passed"
    fi
}

run_clean_db() {
    log_section "Cleaning Database/Cache"
    if [ -d ".next" ]; then
        rm -rf .next
        test ! -e .next || { log_error "Cannot remove .next directory (check ownership: ls -la .next)"; exit 1; }
        log_info "Removed .next directory"
    fi
    if [ -d "node_modules" ]; then
        rm -rf node_modules
        log_info "Removed node_modules directory"
    fi
    log_info "Clean complete"
}

# ── Parse arguments ──
SUBCOMMANDS=()
for arg in "$@"; do
    case "$arg" in
        --help|-h)
            echo "Usage: $0 [typecheck|lint|build|openapi|e2e|quick|full|clean-db]"
            echo ""
            echo "CI Definitions:"
            echo "  quick = typecheck + lint"
            echo "  full  = quick + build + openapi + e2e"
            echo ""
            echo "Commands:"
            echo "  typecheck  - Run TypeScript type check"
            echo "  lint       - Run ESLint"
            echo "  build      - Run Next.js build"
            echo "  openapi    - Run OpenAPI drift check"
            echo "  e2e        - Run Playwright end-to-end tests"
            echo "  quick      - Run quick CI (typecheck + lint)"
            echo "  full       - Run full CI (quick + build + openapi + e2e)"
            echo "  clean-db   - Clean .next and node_modules"
            exit 0
            ;;
        -*) echo "Unknown option: $arg"; exit 1 ;;
        *) SUBCOMMANDS+=("$arg") ;;
    esac
done

if [ ${#SUBCOMMANDS[@]} -eq 0 ]; then SUBCOMMANDS=("quick"); fi

EXPANDED_COMMANDS=()
for cmd in "${SUBCOMMANDS[@]}"; do
    case "$cmd" in
        quick) EXPANDED_COMMANDS+=(typecheck lint) ;;
        full)  EXPANDED_COMMANDS+=(typecheck lint build openapi e2e) ;;
        all)   EXPANDED_COMMANDS+=(typecheck lint) ;;
        *)     EXPANDED_COMMANDS+=("$cmd") ;;
    esac
done

for cmd in "${EXPANDED_COMMANDS[@]}"; do
    case "${cmd}" in
        typecheck) run_typecheck ;;
        lint)      run_lint ;;
        build)     run_build ;;
        openapi)   run_openapi ;;
        e2e)       run_e2e ;;
        clean-db)  run_clean_db ;;
        *) echo "Unknown command: ${cmd}"; exit 1 ;;
    esac
done

echo ""
if [ $FAILED -eq 0 ]; then
    log_info "All checks passed!"; exit 0
else
    log_error "Some checks failed!"; exit 1
fi
