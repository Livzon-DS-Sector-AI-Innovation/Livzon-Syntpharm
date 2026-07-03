#!/bin/bash
# CI entry point — maps CI modes to ci_local.sh subcommands.
#
# Usage:
#   bash scripts/ci.sh           # Default: quick
#   bash scripts/ci.sh quick     # Lint, typecheck, OpenAPI, migration scope (no DB)
#   bash scripts/ci.sh full      # All checks including Alembic and tests (needs PostgreSQL)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-quick}" in
  quick)
    echo "━━━ CI: quick mode ━━━"
    exec bash "$SCRIPT_DIR/ci_local.sh" lint typecheck openapi migration-scope
    ;;
  full)
    echo "━━━ CI: full mode ━━━"
    exec bash "$SCRIPT_DIR/ci_local.sh" all
    ;;
  *)
    echo "Usage: $0 [quick|full]"
    echo ""
    echo "Modes:"
    echo "  quick  - Lint, typecheck, OpenAPI, migration scope (no DB required) [default]"
    echo "  full   - All checks including Alembic and tests (requires PostgreSQL)"
    exit 1
    ;;
esac
