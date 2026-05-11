#!/usr/bin/env bash
set -euo pipefail

# setup_branch_protection.sh
# Configure branch protection on main branch via GitHub CLI.
#
# Usage:
#   ./scripts/setup_branch_protection.sh          # Interactive (asks for confirmation)
#   ./scripts/setup_branch_protection.sh --yes     # Apply without confirmation
#   ./scripts/setup_branch_protection.sh --dry-run # Preview changes only

DRY_RUN=false
YES=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --yes) YES=true ;;
  esac
done

# Check prerequisites
if ! command -v gh &>/dev/null; then
  echo "Error: GitHub CLI (gh) is not installed." >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "Error: jq is not installed." >&2
  exit 1
fi

# Detect repository
REPO="${GITHUB_REPOSITORY:-}"
if [ -z "$REPO" ]; then
  REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)
fi
if [ -z "$REPO" ]; then
  echo "Error: Could not detect repository. Set GITHUB_REPOSITORY or run from a git repo." >&2
  exit 1
fi

echo "Repository: $REPO"
echo ""

# Expected protection settings
EXPECTED=$(cat <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Gate: Lint",
      "Gate: Security",
      "Gate: Dependencies",
      "Gate: Tests",
      "Gate: Docs"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
)

API_URL="repos/$REPO/branches/main/protection"

# Fetch current settings
echo "Fetching current branch protection settings..."
CURRENT=$(gh api "$API_URL" 2>/dev/null || echo "null")

if [ "$CURRENT" = "null" ]; then
  echo "  No existing protection rules found."
  CHANGES=$(echo "$EXPECTED" | jq '{add: .}')
else
  echo "  Existing protection rules detected."
  CHANGES=$(jq -n \
    --argjson expected "$EXPECTED" \
    --argjson current "$CURRENT" \
    '{
      add: $expected,
      remove: null
    }')
fi

echo ""
echo "=== Changes to apply ==="
echo "$CHANGES" | jq '.add' | head -20
if echo "$CHANGES" | jq '.remove != null' | grep -q true; then
  echo "... and removals:"
  echo "$CHANGES" | jq '.remove'
fi

if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "Dry-run mode. No changes applied."
  exit 0
fi

if [ "$YES" = false ]; then
  echo ""
  read -rp "Apply these changes? [y/N] " CONFIRM
  if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted."
    exit 0
  fi
fi

echo ""
echo "Applying branch protection rules..."

echo "$EXPECTED" | gh api \
  -X PUT "$API_URL" \
  --input - \
  --silent

echo ""
echo "Branch protection applied successfully."

# Verify
echo ""
echo "Verifying..."
gh api "$API_URL" --jq '{url, required_status_checks: .required_status_checks.contexts, required_approving_review_count: .required_pull_request_reviews.required_approving_review_count, required_linear_history: .required_linear_history}' 2>/dev/null || echo "Verification failed."
echo ""
echo "Done."
