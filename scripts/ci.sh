#!/bin/bash
# CI entry point — maps CI modes to ci_local.sh subcommands.
#
# Usage:
#   bash scripts/ci.sh <command>
#
# Commands:
#   lint              Ruff check + format check
#   typecheck         Mypy type check
#   openapi           OpenAPI spec drift check
#   migration-scope   Check each migration touches only one module
#   alembic           Apply migrations + drift check (requires PostgreSQL)
#   test              Run pytest (requires PostgreSQL)
#   quick             All quick checks (lint, typecheck, openapi, migration-scope)
#   full              All checks including alembic and test
#
# Default: quick

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-quick}" in
  lint|typecheck|openapi|migration-scope|alembic|test)
    exec bash "$SCRIPT_DIR/ci_local.sh" "$1"
    ;;
  quick)
    echo "━━━ CI: quick mode ━━━"
    exec bash "$SCRIPT_DIR/ci_local.sh" lint typecheck openapi migration-scope
    ;;
  full)
    echo "━━━ CI: full mode ━━━"
    exec bash "$SCRIPT_DIR/ci_local.sh" all
    ;;
  *)
    echo "Usage: $0 [lint|typecheck|openapi|migration-scope|alembic|test|quick|full]"
    echo ""
    echo "Individual commands:"
    echo "  lint              Ruff check + format check"
    echo "  typecheck         Mypy type check"
    echo "  openapi           OpenAPI spec drift check"
    echo "  migration-scope   Check each migration touches only one module"
    echo "  alembic           Apply migrations + drift check (requires PostgreSQL)"
    echo "  test              Run pytest (requires PostgreSQL)"
    echo ""
    echo "Modes:"
    echo "  quick  - All quick checks (no DB required) [default]"
    echo "  full   - All checks including alembic and test (requires PostgreSQL)"
    exit 1
    ;;
esac
