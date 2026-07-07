#!/usr/bin/env python3
"""Create a GitHub Pull Request via API.

Usage:
    python scripts/create_pr.py --title "feat: xxx" --body "xxx" --head "branch-name"

Environment:
    GITHUB_TOKEN - required, your personal access token with `repo` scope.
"""

import argparse
import os
import sys

import httpx

OWNER = "Livzon-DS-Sector-AI-Innovation"
REPO = "XBJ"
BASE = "main"


def create_pr(title: str, body: str, head: str) -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        print("Please set it first:", file=sys.stderr)
        print("   $env:GITHUB_TOKEN='ghp_xxxxxxxx'   (PowerShell)", file=sys.stderr)
        print("   export GITHUB_TOKEN=ghp_xxxxxxxx    (Bash)", file=sys.stderr)
        sys.exit(1)

    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "title": title,
        "body": body,
        "head": head,
        "base": BASE,
    }

    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    data = resp.json()

    if resp.status_code == 201:
        print(f"✅ Pull request created successfully!")
        print(f"   URL: {data['html_url']}")
        print(f"   Number: #{data['number']}")
        return data["html_url"]
    elif resp.status_code == 422 and "A pull request already exists" in str(data):
        print(f"⚠️  A pull request for branch '{head}' already exists.")
        existing = data.get("errors", [{}])[0].get("message", "")
        print(f"   {existing}")
        sys.exit(0)
    else:
        print(f"❌ Failed to create PR (HTTP {resp.status_code}):", file=sys.stderr)
        print(data, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a GitHub Pull Request")
    parser.add_argument("--title", required=True, help="PR title")
    parser.add_argument("--body", default="", help="PR body (markdown)")
    parser.add_argument("--head", required=True, help="Branch name to merge from")
    args = parser.parse_args()
    create_pr(args.title, args.body, args.head)
