#!/usr/bin/env bash
# setup-claude-user.sh
# Configures Claude Code user identity in ~/.claude/settings.json
#
# Curl install:
#   curl -fsSL https://raw.gitlab.barcapint.com/barclays/claude/marketplace/cio/buk/-/raw/main/scripts/setup-claude-user.sh | bash
#
# Non-interactive (CI / onboarding automation):
#   bash setup-claude-user.sh --brid B01234567 --email user@barclays.com --cio DIGITAL --stream "Online Banking"

set -euo pipefail

# ── Platform check ────────────────────────────────────────────────────────────
# Requires bash 3.2+ (macOS default), python3, and a posix-compatible shell.
# Windows: run inside WSL or Git Bash — native CMD/PowerShell is not supported.
if [ "${BASH_VERSION%%.*}" -lt 3 ] 2>/dev/null; then
  echo "Error: bash 3.2 or later required (found $BASH_VERSION)" >&2; exit 1
fi

# ── Canonical CIOs ────────────────────────────────────────────────────────────
# Authoritative list — any other value is invalid
CANONICAL_CIOS=("DIGITAL" "BB" "CCT" "CDAO" "CAPL" "MS&I")

# Human-readable description for each CIO (bash 3.2-compatible — no associative arrays)
cio_desc() {
  case "$1" in
    DIGITAL) echo "Digital" ;;
    BB)      echo "Business Banking" ;;
    CCT)     echo "Customer Care Tech" ;;
    CDAO)    echo "Chief Data & Analytics Office" ;;
    CAPL)    echo "Cards, Unsecured Lending & Payments" ;;
    "MS&I")  echo "Mortgages, Savings & Investments" ;;
    *)       echo "" ;;
  esac
}

# ── CIO alias normaliser ──────────────────────────────────────────────────────
# Maps every known messy legacy variant → canonical. Returns "" if unrecognised.
normalize_cio() {
  local raw="${1:-}"
  # strip leading/trailing whitespace; uppercase for comparison (& is preserved)
  local upper
  upper="$(echo "$raw" | tr '[:lower:]' '[:upper:]' | xargs)"
  case "$upper" in
    DIGITAL|DIGIRTAL)
      echo "DIGITAL" ;;
    BB|BUSINESS_BANKING|BUSINESS-BANKING)
      echo "BB" ;;
    CCT|CUSTOMER_CARE_TECH|CUSTOMER_CARE|CONTACT_CENTER|CONTACTCENTER|CBAI|CUSTOMERCARE_CBAI|CAW|ECC)
      echo "CCT" ;;
    CDAO|BUK_CDAO|RETAIL_CDAO|CCD)
      echo "CDAO" ;;
    CAPL|RETAIL_CAPL|BARCLAYS_API_PLATFORM)
      echo "CAPL" ;;
    "MS&I"|MSI|RETAIL_MSI|"MS_I"|"MS AND I"|"MS&AMP;I")
      echo "MS&I" ;;
    *)
      echo "" ;;
  esac
}

# ── Colour helpers ────────────────────────────────────────────────────────────
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }
dim()    { printf '\033[2m%s\033[0m\n' "$*"; }
die()    { printf '\033[0;31mError: %b\033[0m\n' "$*" >&2; exit 1; }

# ── Settings file location ────────────────────────────────────────────────────
SETTINGS_FILE="${CLAUDE_SETTINGS_FILE:-$HOME/.claude/settings.json}"

# ── Auto-detection helpers ────────────────────────────────────────────────────
detect_brid() {
  local u="${USER:-$(whoami 2>/dev/null || true)}"
  if echo "$u" | grep -qiE '^[a-zA-Z][0-9]{8}$'; then
    echo "$u" | tr '[:lower:]' '[:upper:]'
  else
    echo ""
  fi
}

detect_email() {
  git config --global user.email 2>/dev/null || echo ""
}

read_current_attr() {
  local key="$1"
  [[ -f "$SETTINGS_FILE" ]] || { echo ""; return; }
  python3 - "$SETTINGS_FILE" "$key" <<'PYEOF'
import json, sys
try:
    s = json.load(open(sys.argv[1]))
    attrs = s.get('env', {}).get('OTEL_RESOURCE_ATTRIBUTES', '')
    for pair in attrs.split(','):
        if '=' in pair and pair.split('=', 1)[0].strip() == sys.argv[2]:
            print(pair.split('=', 1)[1].strip())
            sys.exit(0)
except Exception:
    pass
PYEOF
}

# ── Argument parsing ──────────────────────────────────────────────────────────
ARG_BRID="" ARG_EMAIL="" ARG_CIO="" ARG_STREAM=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --brid)    ARG_BRID="$2";   shift 2 ;;
    --email)   ARG_EMAIL="$2";  shift 2 ;;
    --cio)     ARG_CIO="$2";    shift 2 ;;
    --stream)  ARG_STREAM="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--brid B01234567] [--email user@barclays.com] [--cio <cio>] [--stream <stream>]"
      echo ""
      echo "Valid CIOs:"
      for cio in "${CANONICAL_CIOS[@]}"; do
        printf "  %-8s  %s\n" "$cio" "$(cio_desc "$cio")"
      done
      exit 0 ;;
    *) die "Unknown argument: $1 (try --help)" ;;
  esac
done

# ── Sanity checks ─────────────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || die "python3 is required but not found"
[[ -f "$SETTINGS_FILE" ]] || die "Settings file not found: $SETTINGS_FILE\nRun 'claude' once to initialise it, then re-run this script."

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
bold "Claude Code — Barclays user setup"
dim "Updates barclays_user_id, barclays_cio, barclays_stream and barclays_user_email"
echo "Settings: $SETTINGS_FILE"
echo ""

# ── Collect BRID ──────────────────────────────────────────────────────────────
if [[ -n "$ARG_BRID" ]]; then
  BRID="$(echo "$ARG_BRID" | tr '[:lower:]' '[:upper:]')"
else
  default_brid="$(detect_brid)"
  current_brid="$(read_current_attr barclays_user_id)"
  [[ -z "$default_brid" && -n "$current_brid" ]] && default_brid="$current_brid"

  if [[ -n "$default_brid" ]]; then
    read -r -p "BRID [${default_brid}]: " _input
    BRID="$(echo "${_input:-$default_brid}" | tr '[:lower:]' '[:upper:]')"
  else
    read -r -p "BRID (e.g. B01234567): " _input
    BRID="$(echo "$_input" | tr '[:lower:]' '[:upper:]')"
  fi
fi
echo "$BRID" | grep -qiE '^[a-zA-Z][0-9]{8}$' \
  || die "Invalid BRID: '$BRID' — expected one letter + 8 digits (e.g. B01234567, H05946956)"

# ── Collect Email ─────────────────────────────────────────────────────────────
if [[ -n "$ARG_EMAIL" ]]; then
  EMAIL="$ARG_EMAIL"
else
  default_email="$(detect_email)"
  current_email="$(read_current_attr barclays_user_email)"
  [[ -z "$default_email" && -n "$current_email" ]] && default_email="$current_email"
  [[ -z "$default_email" ]] && default_email="$(echo "$BRID" | tr '[:upper:]' '[:lower:]')@barclays.com"

  read -r -p "Email [${default_email}]: " _input
  EMAIL="${_input:-$default_email}"
fi
echo "$EMAIL" | grep -q '@' || die "Invalid email: '$EMAIL'"

# ── Collect CIO ───────────────────────────────────────────────────────────────
if [[ -n "$ARG_CIO" ]]; then
  CIO="$(normalize_cio "$ARG_CIO")"
  if [[ -z "$CIO" ]]; then
    echo ""
    red "Unknown CIO: '$ARG_CIO'"
    echo ""
    echo "Valid values:"
    for cio in "${CANONICAL_CIOS[@]}"; do
      printf "  %-8s  %s\n" "$cio" "${CIO_DESC[$cio]}"
    done
    exit 1
  fi
else
  current_cio="$(read_current_attr barclays_cio)"
  current_cio_canonical="$(normalize_cio "$current_cio")"

  echo ""
  bold "Which CIO do you belong to?"
  echo ""
  for i in "${!CANONICAL_CIOS[@]}"; do
    label="${CANONICAL_CIOS[$i]}"
    suffix=""
    [[ "$label" == "$current_cio_canonical" ]] && suffix=" ← current"
    printf "  %d) %-8s  %s%s\n" $((i+1)) "$label" "$(cio_desc "$label")" "$suffix"
  done
  echo ""

  while true; do
    read -r -p "Enter number (1-${#CANONICAL_CIOS[@]}): " _choice
    if echo "$_choice" | grep -qE '^[0-9]+$' && \
       [[ "$_choice" -ge 1 && "$_choice" -le "${#CANONICAL_CIOS[@]}" ]]; then
      CIO="${CANONICAL_CIOS[$(( _choice - 1 ))]}"
      break
    fi
    yellow "Please enter a number between 1 and ${#CANONICAL_CIOS[@]}"
  done
fi

# ── Collect Work Stream ───────────────────────────────────────────────────────
if [[ -n "$ARG_STREAM" ]]; then
  STREAM="$ARG_STREAM"
else
  current_stream="$(read_current_attr barclays_stream)"

  echo ""
  bold "What is your work stream within ${CIO}?"
  dim "e.g. Retail, Digital Channels, Data Platform, Mobile App"
  echo ""

  if [[ -n "$current_stream" ]]; then
    read -r -p "Work stream [${current_stream}]: " _input
    STREAM="${_input:-$current_stream}"
  else
    read -r -p "Work stream: " _input
    STREAM="$_input"
  fi
fi
[[ -n "$STREAM" ]] || die "Work stream cannot be empty"

# ── Confirm ───────────────────────────────────────────────────────────────────
echo ""
bold "About to write to $SETTINGS_FILE:"
echo ""
echo "  barclays_user_id    = $BRID"
echo "  barclays_user_email = $EMAIL"
echo "  barclays_cio        = $CIO"
echo "  barclays_stream     = $STREAM"
echo ""
read -r -p "Continue? [Y/n]: " _confirm
case "${_confirm:-Y}" in
  [Yy]*) ;;
  *) echo "Aborted."; exit 0 ;;
esac

# ── Patch settings.json ───────────────────────────────────────────────────────
python3 - "$SETTINGS_FILE" "$BRID" "$EMAIL" "$CIO" "$STREAM" <<'PYEOF'
import json, os, sys

settings_file, brid, email, cio, stream = sys.argv[1:]

with open(settings_file) as f:
    settings = json.load(f)

existing = settings.get('env', {}).get('OTEL_RESOURCE_ATTRIBUTES', '')
attrs = {}
for pair in existing.split(','):
    pair = pair.strip()
    if '=' in pair:
        k, v = pair.split('=', 1)
        attrs[k.strip()] = v.strip()

attrs['barclays_user_id']    = brid
attrs['barclays_user_email'] = email
attrs['barclays_cio']        = cio
attrs['barclays_stream']     = stream

# Stable key order — unknown keys preserved at the end
key_order = [
    'barclays_user_id',
    'user_role',
    'team',
    'barclays_cio',
    'barclays_stream',
    'barclays_user_email',
]
ordered = {k: attrs[k] for k in key_order if k in attrs}
for k, v in attrs.items():
    if k not in ordered:
        ordered[k] = v

settings.setdefault('env', {})['OTEL_RESOURCE_ATTRIBUTES'] = ','.join(
    f'{k}={v}' for k, v in ordered.items()
)

# Atomic write — no partial-write corruption
tmp = settings_file + '.tmp'
with open(tmp, 'w') as f:
    json.dump(settings, f, indent=4)
    f.write('\n')
os.replace(tmp, settings_file)
PYEOF

echo ""
green "Done!"
echo ""
dim "Restart Claude Code for changes to take effect."
echo ""
