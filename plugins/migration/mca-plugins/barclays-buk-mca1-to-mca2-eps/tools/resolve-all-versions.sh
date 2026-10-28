#!/bin/bash
# Resolves all versioned MCA1/MCA2 dependencies from Nexus
# Usage: source ./resolve-all-versions.sh [--mca1-prefix=6.2] [--mca2-prefix=2.3]
# Exports: MCA2_BOM, MCA2_AUDIT_LIB, MCA1_BOM, MCA1_SERVICE_LOCATOR,
#          MCA1_LOGGING_SPY, MOCKITO_VERSION

# Resolve script directory (works when sourced in both bash and zsh)
if [ -n "${BASH_SOURCE[0]}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [ -n "${(%):-%x}" ] 2>/dev/null; then
  SCRIPT_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
else
  # Fallback: look for resolver relative to this script's expected location
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
# If SCRIPT_DIR doesn't contain the resolver, search for it
RESOLVER="${SCRIPT_DIR}/resolve-latest-version.sh"
if [ ! -f "$RESOLVER" ]; then
  # Try tools/ subdirectory from CWD (common when sourced from plugin root)
  if [ -f "tools/resolve-latest-version.sh" ]; then
    RESOLVER="$(cd tools && pwd)/resolve-latest-version.sh"
  else
    echo "ERROR: Cannot locate resolve-latest-version.sh" >&2
    return 1 2>/dev/null || exit 1
  fi
fi

# Defaults
MCA1_PREFIX="6.2"
MCA2_PREFIX="2.3"

# Parse optional args
for arg in "$@"; do
  case $arg in
    --mca1-prefix=*) MCA1_PREFIX="${arg#*=}" ;;
    --mca2-prefix=*) MCA2_PREFIX="${arg#*=}" ;;
  esac
done

echo "Resolving dependency versions from Nexus..."
echo "  MCA1 prefix: ${MCA1_PREFIX}"
echo "  MCA2 prefix: ${MCA2_PREFIX}"

FAIL=0

# MCA2 BOM
MCA2_BOM=$("$RESOLVER" "com/barclays/global/mca" "mca-dependencies" "$MCA2_PREFIX")
if [ $? -ne 0 ]; then echo "  FAILED: mca-dependencies (MCA2 BOM)"; FAIL=1; else echo "  mca-dependencies: ${MCA2_BOM}"; fi

# MCA2 audit lib (different group: com.barclays.mca)
MCA2_AUDIT_LIB=$("$RESOLVER" "com/barclays/mca" "mca-eps-libs-audit" "2.0")
if [ $? -ne 0 ]; then echo "  FAILED: mca-eps-libs-audit"; FAIL=1; else echo "  mca-eps-libs-audit: ${MCA2_AUDIT_LIB}"; fi

# MCA1 BOM (for detection/removal)
MCA1_BOM=$("$RESOLVER" "com/barclays/eps" "mca-dependencies" "$MCA1_PREFIX")
if [ $? -ne 0 ]; then echo "  FAILED: mca-dependencies (MCA1 BOM)"; FAIL=1; else echo "  mca-dependencies (MCA1): ${MCA1_BOM}"; fi

# MCA1 service-locator (for detection/removal)
MCA1_SERVICE_LOCATOR=$("$RESOLVER" "com/barclays/global/mca" "mca-service-locator" "1.0")
if [ $? -ne 0 ]; then echo "  FAILED: mca-service-locator"; FAIL=1; else echo "  mca-service-locator: ${MCA1_SERVICE_LOCATOR}"; fi

# MCA1 logging-spy (for detection/removal)
MCA1_LOGGING_SPY=$("$RESOLVER" "com/barclays/global/mca" "mca-logging-spy" "0.1")
if [ $? -ne 0 ]; then echo "  FAILED: mca-logging-spy"; FAIL=1; else echo "  mca-logging-spy: ${MCA1_LOGGING_SPY}"; fi

# Mockito
MOCKITO_VERSION=$("$RESOLVER" "org/mockito" "mockito-core" "5.14")
if [ $? -ne 0 ]; then echo "  FAILED: mockito-core"; FAIL=1; else echo "  mockito-core: ${MOCKITO_VERSION}"; fi

# Spring Boot version (extracted from MCA2 BOM POM)
NEXUS_BASE="https://nexus.barcapint.com/nexus/content/groups/barclays"
if [ -n "$MCA2_BOM" ]; then
  BOM_POM_URL="${NEXUS_BASE}/com/barclays/global/mca/mca-dependencies/${MCA2_BOM}/mca-dependencies-${MCA2_BOM}.pom"
  SPRING_BOOT_VERSION=$(curl -sf --connect-timeout 10 --max-time 30 "$BOM_POM_URL" 2>/dev/null \
    | grep -A1 "spring-boot-dependencies" \
    | grep -oE "<version>[^<]+</version>" \
    | sed 's/<[^>]*>//g' \
    | head -1)
  if [ -z "$SPRING_BOOT_VERSION" ]; then
    echo "  FAILED: Could not extract Spring Boot version from BOM POM"
    FAIL=1
  else
    echo "  spring-boot: ${SPRING_BOOT_VERSION} (from mca-dependencies:${MCA2_BOM} BOM)"
  fi
else
  echo "  FAILED: MCA2_BOM not resolved - cannot determine Spring Boot version"
  FAIL=1
fi

if [ $FAIL -ne 0 ]; then
  echo ""
  echo "ERROR: Critical version resolution failed. Check Nexus connectivity."
  return 1 2>/dev/null || exit 1
fi

export MCA2_BOM MCA2_AUDIT_LIB MCA1_BOM MCA1_SERVICE_LOCATOR MCA1_LOGGING_SPY MOCKITO_VERSION SPRING_BOOT_VERSION
echo ""
echo "All versions resolved successfully."
