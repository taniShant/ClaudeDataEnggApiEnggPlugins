#!/bin/bash
# Analyzes JaCoCo CSV report and outputs ranked coverage gaps
# Usage: ./analyze-coverage-gaps.sh <project_path> [--threshold=70] [--top=15]
# Requires: JaCoCo CSV report at build/reports/jacoco/test/jacocoTestReport.csv
#
# Output:
#   Overall coverage %, per-class ranking by missed instructions,
#   and actionable recommendations for closing the gap.

PROJECT_PATH="$1"
THRESHOLD=70
TOP_N=15

if [ -z "$PROJECT_PATH" ]; then
  echo "ERROR: Usage: $0 <project_path> [--threshold=70] [--top=15]" >&2
  exit 1
fi

for arg in "$@"; do
  case $arg in
    --threshold=*) THRESHOLD="${arg#*=}" ;;
    --top=*) TOP_N="${arg#*=}" ;;
  esac
done

CSV="${PROJECT_PATH}/build/reports/jacoco/test/jacocoTestReport.csv"

if [ ! -f "$CSV" ]; then
  echo "ERROR: JaCoCo report not found at ${CSV}" >&2
  echo "  Run: ./gradlew test jacocoTestReport" >&2
  exit 2
fi

echo "================================================================"
echo " JaCoCo Coverage Gap Analysis"
echo "================================================================"
echo ""

# Calculate overall coverage
TOTAL_COVERED=$(awk -F',' 'NR>1 {sum+=$5} END {print sum}' "$CSV")
TOTAL_MISSED=$(awk -F',' 'NR>1 {sum+=$4} END {print sum}' "$CSV")
TOTAL=$((TOTAL_COVERED + TOTAL_MISSED))

if [ "$TOTAL" -eq 0 ]; then
  echo "ERROR: No instruction data in CSV (empty report?)" >&2
  exit 3
fi

COVERAGE=$(awk "BEGIN {printf \"%.2f\", ($TOTAL_COVERED / $TOTAL) * 100}")
echo "Overall instruction coverage: ${COVERAGE}%"
echo "Threshold:                    ${THRESHOLD}%"
echo "Total instructions:           ${TOTAL} (${TOTAL_COVERED} covered, ${TOTAL_MISSED} missed)"
echo ""

# Check pass/fail
PASS=$(awk "BEGIN {print ($COVERAGE >= $THRESHOLD) ? 1 : 0}")
if [ "$PASS" -eq 1 ]; then
  echo "STATUS: PASS — coverage meets threshold"
  echo ""
fi

DEFICIT=$(awk "BEGIN {printf \"%.0f\", (($THRESHOLD / 100) * $TOTAL) - $TOTAL_COVERED}")
if [ "$PASS" -eq 0 ]; then
  echo "STATUS: FAIL — need ~${DEFICIT} more instructions covered to reach ${THRESHOLD}%"
  echo ""
fi

# Rank classes by missed instructions (highest first)
echo "================================================================"
echo " Top ${TOP_N} Coverage Gaps (by missed instructions)"
echo "================================================================"
echo ""
printf "%-4s %-50s %8s %8s %6s %s\n" "#" "CLASS" "MISSED" "TOTAL" "COV%" "PRIORITY"
printf "%-4s %-50s %8s %8s %6s %s\n" "---" "--------------------------------------------------" "------" "------" "-----" "--------"

# Parse CSV: columns are GROUP,PACKAGE,CLASS,INSTRUCTION_MISSED(4),INSTRUCTION_COVERED(5),...
# Sort by missed instructions descending, show top N
awk -F',' 'NR>1 {
  missed=$4; covered=$5; total=missed+covered;
  if (total > 0) {
    pct=covered*100/total;
  } else {
    pct=100;
  }
  printf "%d\t%s.%s\t%d\t%d\t%.1f\n", missed, $2, $3, missed, total, pct
}' "$CSV" | sort -t$'\t' -k1 -rn | head -"$TOP_N" | awk -F'\t' '{
  rank++;
  if ($3 > 500 && $5 < 50) priority="HIGH";
  else if ($3 > 200) priority="MEDIUM";
  else priority="LOW";
  printf "%-4d %-50s %8d %8d %5.1f%% %s\n", rank, $2, $3, $4, $5, priority
}'

echo ""

# Show classes with 0% coverage (likely new/untested)
ZERO_COUNT=$(awk -F',' 'NR>1 && $5==0 && $4>0 {count++} END {print count+0}' "$CSV")
if [ "$ZERO_COUNT" -gt 0 ]; then
  echo "================================================================"
  echo " Classes with 0% coverage (${ZERO_COUNT} classes)"
  echo "================================================================"
  echo ""
  awk -F',' 'NR>1 && $5==0 && $4>0 {printf "  - %s.%s (%d instructions)\n", $2, $3, $4}' "$CSV" | sort -t'(' -k2 -rn
  echo ""
fi

# Recommendations
if [ "$PASS" -eq 0 ]; then
  echo "================================================================"
  echo " Recommendations (to close ~${DEFICIT} instruction gap)"
  echo "================================================================"
  echo ""
  echo "  1. Target HIGH priority classes first (largest missed count)"
  echo "  2. Re-enable @Disabled tests with MockedStatic where possible"
  echo "  3. Add error-path tests for catch blocks with findCause() patterns"
  echo "  4. Write @SpringBootTest context-loads test for ApplicationConfig"
  echo "  5. Add POJO getter/setter tests (low effort, moderate gain)"
  echo ""
fi
