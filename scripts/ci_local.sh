#!/bin/bash
# Backend CI Local Script
# Usage: ./scripts/ci_local.sh [check|test|all]
# - check: Run lint, format, type-check, openapi, alembic, migration-scope
# - test: Run tests (requires PostgreSQL)
# - all: Run both check and test

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Use CI environment configuration
export APP_ENV=ci

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# Check if PostgreSQL is accessible
check_postgres() {
    if ! uv run python -c "import asyncio; from sqlalchemy.ext.asyncio import create_async_engine; asyncio.run(create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/dazah_ci').dispose())" 2>/dev/null; then
        log_warn "PostgreSQL is not running on localhost:5432"
        log_warn "Some checks will be skipped. Start PostgreSQL with: docker compose up -d db"
        return 1
    fi
    return 0
}

# Run linting checks
run_lint() {
    echo ""
    echo "=== Running Ruff Check ==="
    if ! uv run ruff check .; then
        log_error "Ruff check failed! Run 'uv run ruff check --fix .' to fix issues."
        FAILED=1
    else
        log_info "Ruff check passed"
    fi

    echo ""
    echo "=== Running Ruff Format Check ==="
    if ! uv run ruff format --check .; then
        log_error "Ruff format check failed! Run 'uv run ruff format .' to format code."
        FAILED=1
    else
        log_info "Ruff format check passed"
    fi
}

# Run type checking
run_typecheck() {
    echo ""
    echo "=== Running Mypy Type Check ==="
    if ! uv run mypy app tests; then
        log_error "Mypy type check failed!"
        FAILED=1
    else
        log_info "Mypy type check passed"
    fi
}

# Run OpenAPI check
run_openapi() {
    echo ""
    echo "=== Running OpenAPI Check ==="
    uv run python scripts/export_openapi.py
    if ! git diff --exit-code openapi.json > /dev/null 2>&1; then
        log_error "OpenAPI spec is out of date! Run 'uv run python scripts/export_openapi.py' and commit the changes."
        FAILED=1
    else
        log_info "OpenAPI spec is up to date"
    fi
}

# Run Alembic check (requires PostgreSQL)
run_alembic() {
    if ! check_postgres; then
        log_warn "Skipping Alembic check (PostgreSQL not available)"
        return
    fi

    echo ""
    echo "=== Running Alembic Check ==="
    
    # Apply migrations
    if ! uv run alembic upgrade head; then
        log_error "Failed to apply migrations!"
        FAILED=1
        return
    fi
    log_info "Migrations applied successfully"

    # Check for drift
    if ! uv run alembic check 2>&1 | tee /tmp/alembic-check.log; then
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

# Run migration scope check
run_migration_scope() {
    echo ""
    echo "=== Running Migration Scope Check ==="
    
    MIGRATIONS=$(find alembic/versions -name "*.py" -type f 2>/dev/null)
    
    if [ -z "$MIGRATIONS" ]; then
        log_warn "No migration files found"
        return
    fi
    
    SCOPE_FAILED=0
    for migration in $MIGRATIONS; do
        if ! python scripts/check_migration_scope.py "$migration"; then
            SCOPE_FAILED=1
        fi
    done
    
    if [ $SCOPE_FAILED -eq 1 ]; then
        log_error "Migration scope check failed! Each migration should only modify one module's schema."
        FAILED=1
    else
        log_info "All migrations follow single-module principle"
    fi
}

# Run tests (requires PostgreSQL)
run_tests() {
    if ! check_postgres; then
        log_error "PostgreSQL is required for tests. Start with: docker compose up -d postgres"
        FAILED=1
        return
    fi

    echo ""
    echo "=== Running Tests ==="
    
    # Apply migrations before running tests
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

# Main
case "${1:-all}" in
    check)
        run_lint
        run_typecheck
        run_openapi
        run_alembic
        run_migration_scope
        ;;
    test)
        run_tests
        ;;
    all)
        run_lint
        run_typecheck
        run_openapi
        run_alembic
        run_migration_scope
        run_tests
        ;;
    *)
        echo "Usage: $0 [check|test|all]"
        echo "  check: Run lint, format, type-check, openapi, alembic, migration-scope"
        echo "  test:  Run tests (requires PostgreSQL)"
        echo "  all:   Run both check and test"
        exit 1
        ;;
esac

echo ""
if [ $FAILED -eq 0 ]; then
    log_info "All checks passed!"
    exit 0
else
    log_error "Some checks failed!"
    exit 1
fi
