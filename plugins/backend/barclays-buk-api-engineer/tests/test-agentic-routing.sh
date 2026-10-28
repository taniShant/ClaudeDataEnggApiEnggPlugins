#!/bin/bash
# ============================================================================
# Structural validation for api-engineer-agentic-agent.md
#
# Validates that the agent definition contains required patterns for correct
# SPEC_TYPE routing, input normalization, and workflow delegation.
#
# Usage:
#   cd plugins/backend/barclays-buk-api-engineer
#   bash tests/test-agentic-routing.sh
#
# Exit code: 0 = all passed, 1 = one or more failures
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENT_FILE="$PLUGIN_DIR/agents/api-engineer-agentic-agent.md"

PASS=0
FAIL=0
TOTAL=0

# Colors (safe for terminals that don't support them)
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

check() {
  local desc="$1"
  local pattern="$2"
  ((TOTAL++))
  if grep -qiE "$pattern" "$AGENT_FILE" 2>/dev/null; then
    echo -e "  ${GREEN}PASS${NC}: $desc"
    ((PASS++))
  else
    echo -e "  ${RED}FAIL${NC}: $desc"
    echo "        Expected pattern: $pattern"
    ((FAIL++))
  fi
}

check_absent() {
  local desc="$1"
  local pattern="$2"
  ((TOTAL++))
  if grep -qiE "$pattern" "$AGENT_FILE" 2>/dev/null; then
    echo -e "  ${RED}FAIL${NC}: $desc"
    echo "        Found pattern that should be absent: $pattern"
    ((FAIL++))
  else
    echo -e "  ${GREEN}PASS${NC}: $desc"
    ((PASS++))
  fi
}

echo "=============================================="
echo "AGENTIC ROUTING STRUCTURAL VALIDATION"
echo "=============================================="
echo ""
echo "Agent file: $AGENT_FILE"
echo ""

if [ ! -f "$AGENT_FILE" ]; then
  echo -e "${RED}FATAL: Agent file not found${NC}"
  exit 1
fi

# --------------------------------------------------------------------------
echo "--- 1. OPERATION Input ---"
# --------------------------------------------------------------------------

check "OPERATION input is declared in Your Inputs section" \
  "OPERATION:.*generate.*validate.*refine.*fix"

check "OPERATION input includes auto as default" \
  'OPERATION:.*"auto"'

# --------------------------------------------------------------------------
echo ""
echo "--- 2. Input Normalisation (Step -1) ---"
# --------------------------------------------------------------------------

check "Step -1 section exists" \
  "Step -1.*Normalize|Step -1.*Normalise"

check "SPEC_TYPE lowercase normalisation documented" \
  "SPEC_TYPE.*trim.*lowercase|lowercase.*SPEC_TYPE|convert to lowercase"

check "OPERATION lowercase normalisation documented" \
  "OPERATION.*trim.*lowercase|lowercase.*OPERATION"

# --------------------------------------------------------------------------
echo ""
echo "--- 3. SPEC_TYPE Validation ---"
# --------------------------------------------------------------------------

check "Unsupported SPEC_TYPE error message exists" \
  "Unsupported SPEC_TYPE|INPUT VALIDATION FAILED.*SPEC_TYPE"

check "Allowed SPEC_TYPE values listed" \
  "daf.*smesh.*auto|Allowed:.*daf"

# --------------------------------------------------------------------------
echo ""
echo "--- 4. OPERATION Validation ---"
# --------------------------------------------------------------------------

check "Unsupported OPERATION error message exists" \
  "Unsupported OPERATION|INPUT VALIDATION FAILED.*OPERATION"

# --------------------------------------------------------------------------
echo ""
echo "--- 5. Step 0 Explicit Override Hardening ---"
# --------------------------------------------------------------------------

check "Step 0 has NEVER fall through guard" \
  "NEVER fall through to Step 1"

check "Step 0.1 OPERATION-based resolution exists" \
  "Step 0\.1.*OPERATION|OPERATION-based Resolution"

check "Step 0.2 INTENT keyword resolution exists" \
  "Step 0\.2.*INTENT|Keyword Resolution"

check "Step 0.3 default resolution exists" \
  "Step 0\.3.*Default|Default Resolution"

check "Default for smesh is sMesh Generate" \
  "smesh.*sMesh Generate|smesh.*default.*sMesh"

check "Default for daf is DAF Generate" \
  "daf.*DAF Generate|daf.*default.*DAF"

check "explicit-override-operation classification method documented" \
  "explicit-override-operation"

check "explicit-override-keyword classification method documented" \
  "explicit-override-keyword"

check "explicit-override-default classification method documented" \
  "explicit-override-default"

# --------------------------------------------------------------------------
echo ""
echo "--- 6. Step 4B Delegation (sMesh Generate) ---"
# --------------------------------------------------------------------------

check "Step 4B references generate.md workflow" \
  "generate\.md"

check "Step 4B contains CRITICAL warning against direct delegation" \
  "Do NOT invoke.*project-generation-agent directly|CRITICAL.*Do NOT"

check "Step 4B documents full pipeline steps (spec parsing, SDK, compilation)" \
  "spec-parsing-agent.*SPEC_ANALYSIS|spec parsing.*standards.*SDK.*compilation"

check_absent "Step 4B does NOT contain Task(subagent_type: project-generation-agent)" \
  "4B.*Task\(.*subagent_type.*project-generation-agent"

# --------------------------------------------------------------------------
echo ""
echo "--- 7. Step 4I Delegation (TDD Generate) ---"
# --------------------------------------------------------------------------

check "Step 4I references tdd.md workflow" \
  "tdd\.md"

check "Step 4I contains CRITICAL warning against direct delegation" \
  "Do NOT invoke.*tdd-orchestrator-agent.*directly"

check_absent "Step 4I does NOT contain Task(subagent_type: tdd-orchestrator-agent)" \
  "4I.*Task\(.*subagent_type.*tdd-orchestrator-agent"

# --------------------------------------------------------------------------
echo ""
echo "--- 8. Input Defaults Table ---"
# --------------------------------------------------------------------------

check "OPERATION default documented in Input defaults table" \
  'OPERATION.*"auto".*Inferred|OPERATION.*auto.*default'

# --------------------------------------------------------------------------
echo ""
echo "--- 9. Capability-to-Command Mapping ---"
# --------------------------------------------------------------------------

check "sMesh Generate maps to generate.md pipeline in mapping table" \
  "sMesh Generate.*generate\.md"

check "TDD Generate maps to tdd.md pipeline in mapping table" \
  "TDD Generate.*tdd\.md"

# --------------------------------------------------------------------------
echo ""
echo "--- 10. Examples ---"
# --------------------------------------------------------------------------

check "Example includes SPEC_TYPE: smesh" \
  "SPEC_TYPE: +smesh"

check "Example includes OPERATION: generate" \
  "OPERATION: +generate"

# --------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "RESULTS"
echo "=============================================="
echo ""
echo -e "  Passed: ${GREEN}${PASS}${NC}"
echo -e "  Failed: ${RED}${FAIL}${NC}"
echo -e "  Total:  ${TOTAL}"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}ALL CHECKS PASSED ✓${NC}"
  exit 0
else
  echo -e "${RED}${FAIL} CHECK(S) FAILED ✗${NC}"
  exit 1
fi
