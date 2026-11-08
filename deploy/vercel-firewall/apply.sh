#!/usr/bin/env bash
# Apply the custom Vercel Firewall rules in rules.json to the linked project.
#
#   deploy/vercel-firewall/apply.sh             # add missing rules, then publish
#   deploy/vercel-firewall/apply.sh --dry-run   # print the commands only
#
# Safe to re-run: a rule whose name already exists on the project (published
# or staged as a draft) is skipped. See README.md in this folder.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RULES_FILE="${RULES_FILE:-$SCRIPT_DIR/rules.json}"
PROJECT_NAME="${VERCEL_PROJECT_NAME:-}"
DRY_RUN=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [--dry-run] [--project NAME]

  --dry-run       Print the vercel commands instead of running them.
  --project NAME  Project name for 'vercel firewall publish --confirm-name'.
                  Defaults to projectName in .vercel/project.json.
  -h, --help      Show this help.

Environment: RULES_FILE (default: rules.json next to this script),
             VERCEL_PROJECT_NAME (same as --project).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --project) PROJECT_NAME="${2:?--project needs a value}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

die()  { echo "error: $*" >&2; exit 1; }
warn() { echo "warning: $*" >&2; }
info() { echo "==> $*"; }

# Quote one argument for display, so a printed command can be copy-pasted.
shell_quote() {
  local s="$1" sq="'" esc="'\\''"
  if [[ "$s" =~ ^[A-Za-z0-9_./:=@+-]+$ ]]; then
    printf '%s' "$s"
  else
    printf "'%s'" "${s//$sq/$esc}"
  fi
}

# Run a command, or only print it under --dry-run.
run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    local out="+" arg
    for arg in "$@"; do out+=" $(shell_quote "$arg")"; done
    echo "$out"
  else
    "$@"
  fi
}

# --- Prerequisites ----------------------------------------------------------

command -v jq >/dev/null 2>&1 \
  || die "jq is required to read rules.json. Install it with 'brew install jq' (macOS) or 'apt-get install jq'."

[[ -f "$RULES_FILE" ]] || die "rules file not found: $RULES_FILE"
jq -e 'type == "array" and length > 0 and all(.[]; (.name | type) == "string")' \
  "$RULES_FILE" >/dev/null \
  || die "$RULES_FILE must be a non-empty JSON array of rules, each with a string \"name\"."

cd "$REPO_ROOT"

HAVE_VERCEL=1
if ! command -v vercel >/dev/null 2>&1; then
  HAVE_VERCEL=0
  msg="the vercel CLI is not installed. Install it with 'npm i -g vercel', then run 'vercel login'."
  if [[ $DRY_RUN -eq 1 ]]; then warn "$msg"; else die "$msg"; fi
fi

LINKED=1
if [[ ! -f .vercel/project.json ]]; then
  LINKED=0
  msg="this checkout is not linked to a Vercel project. Run 'vercel link --scope reubenzstechs' in $REPO_ROOT first."
  if [[ $DRY_RUN -eq 1 ]]; then warn "$msg"; else die "$msg"; fi
fi

if [[ -z "$PROJECT_NAME" && $LINKED -eq 1 ]]; then
  PROJECT_NAME="$(jq -r '.projectName // empty' .vercel/project.json)"
fi

# --- Current rules ----------------------------------------------------------

EXISTING_NAMES=""
if [[ $DRY_RUN -eq 1 ]]; then
  info "Current firewall rules (dry run: not fetched, so no rule is skipped)"
  run vercel firewall rules list
else
  info "Current firewall rules (including unpublished drafts)"
  vercel firewall rules list
  # Collect every "name" in the JSON listing, whatever its exact shape.
  EXISTING_NAMES="$(vercel firewall rules list --json \
    | jq -r '[.. | objects | select((.name? | type) == "string") | .name] | unique | .[]')"
fi

# --- Add missing rules, in priority order -----------------------------------

added=0
skipped=0
count="$(jq 'length' "$RULES_FILE")"
for ((i = 0; i < count; i++)); do
  name="$(jq -r ".[$i].name" "$RULES_FILE")"
  data="$(jq -c ".[$i]" "$RULES_FILE")"
  if [[ -n "$EXISTING_NAMES" ]] && grep -Fxq -- "$name" <<<"$EXISTING_NAMES"; then
    info "Skip  [$((i + 1))/$count] $name (already exists)"
    skipped=$((skipped + 1))
    continue
  fi
  info "Add   [$((i + 1))/$count] $name"
  run vercel firewall rules add --data "$data" --yes
  added=$((added + 1))
done

# --- Review and publish -----------------------------------------------------

info "Staged changes"
run vercel firewall diff

if [[ $added -eq 0 ]]; then
  info "No new rules ($skipped already present). Nothing to publish."
  echo "    If the diff above still shows staged drafts, publish them with:"
  echo "    vercel firewall publish${PROJECT_NAME:+ --confirm-name $PROJECT_NAME}"
  exit 0
fi

info "Publishing $added new rule(s)"
if [[ -n "$PROJECT_NAME" ]]; then
  run vercel firewall publish --confirm-name "$PROJECT_NAME"
else
  [[ $DRY_RUN -eq 1 ]] && warn "project name unknown; publish will ask you to type it."
  run vercel firewall publish
fi

if [[ $DRY_RUN -eq 1 ]]; then
  info "Dry run complete: nothing was changed on Vercel."
else
  info "Done. Check the result with: vercel firewall rules list --expand"
fi
