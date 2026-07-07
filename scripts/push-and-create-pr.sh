#!/usr/bin/env bash
# Usage: bash scripts/push-and-create-pr.sh "branch-name" "PR title"
set -e

BRANCH="${1:-$(git branch --show-current)}"
TITLE="${2:-feat: update from local}"
REMOTE="${3:-xbj}"

echo "🔼 Pushing branch '$BRANCH' to remote '$REMOTE'..."
git push "$REMOTE" "$BRANCH"

echo "📬 Creating pull request..."
cd "$(dirname "$0")/.."
uv run python scripts/create_pr.py \
  --title "$TITLE" \
  --body "Pushed from local development environment." \
  --head "$BRANCH"
