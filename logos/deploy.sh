#!/usr/bin/env bash
# deploy.sh — Deploy all websites to Cloudflare Pages
#
# Usage:
#   ./deploy.sh                  # deploy all ready sites
#   ./deploy.sh --dry-run        # check readiness, no deploy
#   ./deploy.sh --site fishinglog-ai-site  # deploy single site
#   ./deploy.sh --list           # list sites and readiness
#
# Prerequisites:
#   - wrangler >= 4.x installed and authenticated (wrangler whoami)
#   - Each site directory must contain at minimum an index.html
#
# Sites:
#   1. lucineer-com-site     — lucineer.com (static HTML/CSS/JS)
#   2. activelog-ai-site     — activelog.ai (static landing page)
#   3. fishinglog-ai-site    — fishinglog.ai (Pages Functions + KV)
#   4. activeledger-ai-site  — activeledger.ai (static with wrangler.toml)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTS_DIR="/home/eileen/projects"

# ── Site registry ───────────────────────────────────────────────

declare -A SITE_PROJECT_NAMES=(
  ["lucineer-com-site"]="lucineer-com"
  ["activelog-ai-site"]="activelog-ai"
  ["fishinglog-ai-site"]="fishinglog-ai-site"
  ["activeledger-ai-site"]="activeledger-ai"
)

SITES=(
  "lucineer-com-site"
  "activelog-ai-site"
  "fishinglog-ai-site"
  "activeledger-ai-site"
)

# ── Colors ──────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

ok()  { echo -e "  ${GREEN}✓${NC} $*"; }
warn(){ echo -e "  ${YELLOW}⚠${NC} $*"; }
err() { echo -e "  ${RED}✗${NC} $*"; }
info(){ echo -e "  ${CYAN}→${NC} $*"; }
hdr() { echo -e "\n${BOLD}═══ $* ═══${NC}"; }

# ── Prerequisites ───────────────────────────────────────────────

check_wrangler() {
  if ! command -v wrangler &>/dev/null; then
    err "wrangler not found. Install: npm install -g wrangler@latest"
    return 1
  fi

  local version
  version=$(wrangler --version 2>/dev/null | head -1 || true)
  if [[ -z "$version" ]]; then
    err "wrangler not authenticated. Run: wrangler login"
    return 1
  fi
  ok "wrangler $version"
}

# ── Site readiness check ────────────────────────────────────────

check_site() {
  local name="$1"
  local dir="$PROJECTS_DIR/$name"

  echo ""
  echo -e "${BOLD}${name}${NC}"

  if [[ ! -d "$dir" ]]; then
    err "directory not found: $dir"
    return 1
  fi

  local ready=true

  if [[ -f "$dir/index.html" ]]; then
    ok "index.html"
  else
    err "missing index.html"
    ready=false
  fi

  if [[ -f "$dir/wrangler.toml" ]] || [[ -f "$dir/wrangler.jsonc" ]]; then
    ok "wrangler config present"
  else
    warn "no wrangler config (will use --project-name flag)"
  fi

  if [[ -d "$dir/functions" ]]; then
    local fn_count
    fn_count=$(find "$dir/functions" -name '*.js' -o -name '*.ts' 2>/dev/null | wc -l)
    ok "Pages Functions: ${fn_count} handler(s)"
  fi

  # Check git status for uncommitted changes
  if [[ -d "$dir/.git" ]]; then
    if git -C "$dir" diff --quiet --exit-code 2>/dev/null; then
      ok "git clean"
    else
      warn "git has uncommitted changes — commit before deploying"
    fi
  else
    warn "not a git repo"
  fi

  # Count assets
  local html_count css_count js_count
  html_count=$(find "$dir" -maxdepth 2 -name '*.html' 2>/dev/null | wc -l)
  css_count=$(find "$dir" -maxdepth 2 -name '*.css' 2>/dev/null | wc -l)
  js_count=$(find "$dir" -maxdepth 2 -name '*.js' 2>/dev/null | wc -l)
  info "${html_count} html  ${css_count} css  ${js_count} js"

  if [[ "$ready" == "true" ]]; then
    echo -e "  Status: ${GREEN}READY${NC}"
    return 0
  else
    echo -e "  Status: ${RED}NOT READY${NC}"
    return 1
  fi
}

# ── Deploy single site ─────────────────────────────────────────

deploy_site() {
  local name="$1"
  local dir="$PROJECTS_DIR/$name"
  local project="${SITE_PROJECT_NAMES[$name]}"

  hdr "Deploying $name → $project"

  # Readiness check
  if ! check_site "$name" >/dev/null 2>&1; then
    err "site not ready — skipping"
    return 1
  fi

  # Build the wrangler command
  local cmd="wrangler pages deploy \"$dir\" --project-name \"$project\""

  # Add branch from git if available
  local branch=""
  if [[ -d "$dir/.git" ]]; then
    branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [[ -n "$branch" && "$branch" != "HEAD" ]]; then
      cmd="$cmd --branch \"$branch\""
    fi
  fi

  # Add commit hash as commit message
  local commit_sha=""
  if [[ -d "$dir/.git" ]]; then
    commit_sha=$(git -C "$dir" rev-parse --short HEAD 2>/dev/null || echo "")
    if [[ -n "$commit_sha" ]]; then
      cmd="$cmd --commit-dirty=true"
    fi
  fi

  info "command: $cmd"
  echo ""

  # Execute
  if eval "$cmd"; then
    ok "deployed successfully"
    echo -e "  ${GREEN}URL: https://${project}.pages.dev${NC}"
    return 0
  else
    err "deployment failed"
    return 1
  fi
}

# ── List sites ──────────────────────────────────────────────────

list_sites() {
  echo -e "${BOLD}Website Inventory${NC}"
  echo ""

  for site in "${SITES[@]}"; do
    local dir="$PROJECTS_DIR/$site"
    local project="${SITE_PROJECT_NAMES[$site]}"
    local status=""

    if [[ -d "$dir" && -f "$dir/index.html" ]]; then
      status="${GREEN}ready${NC}"
    elif [[ -d "$dir" ]]; then
      status="${YELLOW}incomplete${NC}"
    else
      status="${RED}missing${NC}"
    fi

    printf "  %-28s → %-22s  %b\n" "$site" "$project.pages.dev" "$status"
  done
  echo ""
}

# ── Main ────────────────────────────────────────────────────────

main() {
  local mode="deploy"
  local target=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run|-n)
        mode="check"
        shift
        ;;
      --list|-l)
        list_sites
        return 0
        ;;
      --site|-s)
        target="$2"
        shift 2
        ;;
      --help|-h)
        echo "Usage: $0 [--dry-run|-n] [--list|-l] [--site <name>|-s <name>]"
        echo ""
        echo "Deploy websites to Cloudflare Pages."
        echo ""
        echo "Options:"
        echo "  --dry-run, -n    Check readiness only, skip deployment"
        echo "  --list, -l       List all sites and their status"
        echo "  --site, -s NAME  Deploy a single site by name"
        echo ""
        echo "Sites:"
        for s in "${SITES[@]}"; do
          echo "  $s  →  ${SITE_PROJECT_NAMES[$s]}.pages.dev"
        done
        return 0
        ;;
      *)
        err "unknown flag: $1"
        return 1
        ;;
    esac
  done

  # Prequisites
  echo -e "${BOLD}╔═══════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║   Cloudflare Pages — Multi-Site Deployer              ║${NC}"
  echo -e "${BOLD}╚═══════════════════════════════════════════════════════╝${NC}"
  echo ""

  if ! check_wrangler; then
    return 1
  fi

  # Determine which sites to process
  local to_process=()
  if [[ -n "$target" ]]; then
    if [[ -d "$PROJECTS_DIR/$target" ]]; then
      to_process=("$target")
    else
      err "unknown site: $target"
      list_sites
      return 1
    fi
  else
    to_process=("${SITES[@]}")
  fi

  # Check or deploy
  local success=0
  local failed=0

  for site in "${to_process[@]}"; do
    if [[ "$mode" == "check" ]]; then
      if check_site "$site"; then
        ((success++))
      else
        ((failed++))
      fi
    else
      if deploy_site "$site"; then
        ((success++))
      else
        ((failed++))
      fi
    fi
  done

  # Summary
  hdr "Summary"
  echo -e "  ${GREEN}${success} succeeded${NC}  ${RED}${failed} failed${NC}  of ${#to_process[@]} total"
  echo ""
}

main "$@"
