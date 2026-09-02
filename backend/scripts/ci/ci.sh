#!/bin/bash
# Backend CI — domain checks only.
# Cross-project checks (openapi, e2e) live at root: scripts/ci.sh
#
# Usage:
#   ./scripts/ci/ci.sh [subcommand] [options]
#
# Subcommands:
#   lint              Ruff check + format check
#   typecheck         Mypy type check
#   alembic           Apply migrations + drift check (requires PostgreSQL)
#   migration-scope   Check each migration touches only one module
#   test              Run pytest (requires PostgreSQL, runs migrations first)
#
#
# Options:
#   --clean-db        Drop and recreate the CI database before running
#                     (only affects subcommands that use the database)
#   --help, -h        Show this help message
#
# Environment:
#   - In GitHub Actions: assumes env vars and services are pre-configured.
#   - Locally: loads .env.ci (APP_ENV=ci) if present.
#
# GitHub Actions workflow should:
#   1. Checkout, install Python + uv, sync dependencies
#   2. Start PostgreSQL service (for db-requiring jobs)
#   3. Set env vars (DATABASE_URL, FEISHU__PLATFORM__*, etc.)
#   4. Call: bash scripts/ci_local.sh <subcommand>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

REPO_ROOT="$(dirname "$PROJECT_ROOT")"
CI_COMPOSE_FILE="$REPO_ROOT/docker-compose.ci.yml"

STARTED_CI_PG=false
cleanup_ci_pg() {
    if [ "$STARTED_CI_PG" = "true" ]; then
        log_info "Stopping CI postgres..."
        docker compose -f "$CI_COMPOSE_FILE" down -v postgres 2>/dev/null || true
    fi
}
trap cleanup_ci_pg EXIT

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=0

log_info()  { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}❌${NC} $1"; }
log_warn()  { echo -e "${YELLOW}⚠️${NC} $1"; }

show_help() {
    sed -n '1,/^# GitHub Actions workflow should:/p' "$0" | grep '^#' | sed 's/^# \?//'
}

# ── Detect environment ──────────────────────────────────────────────────────
if [ "${GITHUB_ACTIONS}" = "true" ]; then
    CI_MODE=true
else
    CI_MODE=false
    # Locally, use CI env config so results match GitHub Actions
    if [ -z "${APP_ENV}" ] && [ -f ".env.ci" ]; then
        export APP_ENV=ci
    fi
fi

# ── Parse options ───────────────────────────────────────────────────────────
CLEAN_DB=false
SUBCOMMANDS=()

for arg in "$@"; do
    case "$arg" in
        --clean-db)
            CLEAN_DB=true
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        -*)
            echo "Unknown option: $arg"
            show_help
            exit 1
            ;;
        *)
            SUBCOMMANDS+=("$arg")
            ;;
    esac
done

# Default to showing help if no subcommand given
if [ ${#SUBCOMMANDS[@]} -eq 0 ]; then
    show_help
    exit 1
fi

# ── Database helpers ────────────────────────────────────────────────────────
DB_URL="${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@localhost:5432/dazah_ci}"
# Extract DB name from URL for psql commands
DB_NAME="${DB_URL##*/}"
DB_HOST="${DB_URL#*://}"
DB_HOST="${DB_HOST%%/*}"
DB_HOST="${DB_HOST%%:*}"
DB_HOST="${DB_HOST%@*}"
# Default host for psql
PSQL_HOST="${DB_HOST:-localhost}"

check_postgres() {
    if ! uv run python -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
async def check():
    engine = create_async_engine('${DB_URL}')
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        return True
    finally:
        await engine.dispose()
asyncio.run(check())
" 2>/dev/null; then
        return 1
    fi
    return 0
}

ensure_postgres() {
    if check_postgres; then
        return
    fi
    if [ "${CI_MODE}" = "true" ]; then
        log_error "PostgreSQL is not accessible at ${PSQL_HOST}:5432"
        log_error "GitHub Actions should have started a postgres service."
        exit 1
    fi
    log_info "Starting CI postgres container..."
    docker compose -f "$CI_COMPOSE_FILE" up -d postgres
    STARTED_CI_PG=true
    for i in $(seq 1 30); do
        if check_postgres; then
            log_info "CI postgres ready"
            return
        fi
        sleep 1
    done
    log_error "CI postgres did not become ready"
    exit 1
}

clean_db() {
    if [ "${CLEAN_DB}" != "true" ]; then
        return
    fi
    ensure_postgres
    log_warn "Dropping and recreating database '${DB_NAME}'..."
    # Use psql via docker compose locally, or direct psql in CI
    if [ "${CI_MODE}" = "true" ]; then
        PSQL_CMD="psql -h ${PSQL_HOST} -U postgres"
    else
        PSQL_CMD="docker compose -f \"$CI_COMPOSE_FILE\" exec -T postgres psql -U postgres"
    fi
    ${PSQL_CMD} -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" 2>/dev/null || true
    ${PSQL_CMD} -c "DROP DATABASE IF EXISTS \"${DB_NAME}\";" 2>/dev/null || true
    ${PSQL_CMD} -c "CREATE DATABASE \"${DB_NAME}\";" 2>/dev/null || true
    log_info "Database '${DB_NAME}' recreated."
}

# ── Check functions ─────────────────────────────────────────────────────────
run_lint() {
    echo ""
    echo "=== Ruff Check ==="
    if ! uv run ruff check .; then
        log_error "Ruff check failed! Run 'uv run ruff check --fix .' to fix."
        FAILED=1
    else
        log_info "Ruff check passed"
    fi

    echo ""
    echo "=== Ruff Format Check ==="
    if ! uv run ruff format --check .; then
        log_error "Ruff format check failed! Run 'uv run ruff format .' to format."
        FAILED=1
    else
        log_info "Ruff format check passed"
    fi
}

run_typecheck() {
    echo ""
    echo "=== Mypy Type Check ==="
    rm -rf .mypy_cache
    if ! uv run mypy app tests --explicit-package-bases; then
        log_error "Mypy type check failed!"
        FAILED=1
    else
        log_info "Mypy type check passed"
    fi
}

run_alembic() {
    echo ""
    echo "=== Alembic Check ==="
    ensure_postgres
    clean_db
    export DATABASE_URL="$DB_URL"

    local HEAD_COUNT
    HEAD_COUNT=$(uv run alembic heads 2>&1 | grep -c '(head)')
    if [ "$HEAD_COUNT" -gt 1 ]; then
        log_error "Multiple alembic heads detected ($HEAD_COUNT)!"
        uv run alembic heads
        FAILED=1
        return
    fi
    log_info "Single alembic head (OK)"

    if ! uv run alembic upgrade head; then
        log_error "Failed to apply migrations!"
        FAILED=1
        return
    fi
    log_info "Migrations applied successfully"

    if ! uv run alembic current 2>&1; then
        log_error "Failed to verify alembic current state!"
        FAILED=1
    else
        log_info "Alembic current state verified"
    fi

    if ! uv run alembic check 2>&1; then
        log_error "Model changes detected without corresponding Alembic migration!"
        echo ""
        echo "Please run:"
        echo "  docker compose exec app .venv/bin/alembic revision --autogenerate -m 'describe your changes'"
        echo ""
        FAILED=1
    else
        log_info "All models are covered by migrations"
    fi
}

run_migration_scope() {
    echo ""
    echo "=== Migration Scope Check ==="

    MIGRATIONS=$(find alembic/versions -name "*.py" -type f 2>/dev/null)

    if [ -z "${MIGRATIONS}" ]; then
        log_warn "No migration files found"
        return
    fi

    SCOPE_FAILED=0
    for migration in ${MIGRATIONS}; do
        if ! python3 scripts/ci/check_migration_scope.py "${migration}"; then
            SCOPE_FAILED=1
        fi
    done

    if [ ${SCOPE_FAILED} -eq 1 ]; then
        log_error "Migration scope check failed! Each migration should only modify one module's schema."
        FAILED=1
    else
        log_info "All migrations follow single-module principle"
    fi
}

run_tests() {
    echo ""
    echo "=== Tests ==="
    ensure_postgres
    clean_db
    export DATABASE_URL="$DB_URL"

    # Apply migrations before tests (tests need schema)
    echo "Applying database migrations..."
    if ! uv run alembic upgrade head; then
        log_error "Failed to apply migrations!"
        FAILED=1
        return
    fi
    log_info "Migrations applied"

    if ! uv run pytest; then
        log_error "Tests failed!"
        FAILED=1
    else
        log_info "All tests passed"
    fi
}

# ── Dispatch ────────────────────────────────────────────────────────────────
for cmd in "${SUBCOMMANDS[@]}"; do
    case "${cmd}" in
        lint)            run_lint ;;
        typecheck|mypy)  run_typecheck ;;
        alembic)         run_alembic ;;
        migration-scope) run_migration_scope ;;
        test)            run_tests ;;
        *)
            echo "Unknown subcommand: ${cmd}"
            echo ""
            show_help
            exit 1
            ;;
    esac
done

echo ""
if [ ${FAILED} -eq 0 ]; then
    log_info "All checks passed!"
    exit 0
else
    log_error "Some checks failed!"
    exit 1
fi
