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
    if ! docker compose -f "$ROOT_DIR/docker-compose.ci.yml" run --rm --build ci-build sh -c "pnpm build"; then
        log_error "Build failed!"; FAILED=1
    else
        log_info "Build passed"
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
            echo "Usage: $0 [typecheck|lint|build|clean-db]"
            echo ""
            echo "Domain CI checks. Cross-project checks (openapi, e2e) at root: scripts/ci.sh"
            echo ""
            echo "Commands:"
            echo "  typecheck  - Run TypeScript type check"
            echo "  lint       - Run ESLint"
            echo "  build      - Run Next.js build"
            echo "  clean-db   - Clean .next and node_modules"
            exit 0
            ;;
        -*) echo "Unknown option: $arg"; exit 1 ;;
        *) SUBCOMMANDS+=("$arg") ;;
    esac
done

if [ ${#SUBCOMMANDS[@]} -eq 0 ]; then
    echo "Usage: $0 [typecheck|lint|build|clean-db]"
    echo "Cross-project checks (openapi, e2e) at root: scripts/ci.sh"
    exit 1
fi

for cmd in "${SUBCOMMANDS[@]}"; do
    case "${cmd}" in
        typecheck) run_typecheck ;;
        lint)      run_lint ;;
        build)     run_build ;;
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
