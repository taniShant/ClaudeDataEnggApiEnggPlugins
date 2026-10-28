# Detection Runner Guide: Automated Analysis

## Executive Summary

Guide for running automated pattern detection on codebases to assess MCA2 EPS framework integration. Includes shell scripts, Python tools, and CI/CD integration examples.

---

## Quick Start: 30-Second Detection

```bash
#!/bin/bash
# Run this in your project root to get instant framework score

echo "=== MCA2 EPS Framework Detection ==="

FILTER=$(rg "extends OncePerRequestFilter" src/ --type java 2>/dev/null | wc -l)
CONTEXT=$(rg "@IOLContext" src/ --type java 2>/dev/null | wc -l)
EXCEPT=$(rg "extends GenericException" src/ --type java 2>/dev/null | wc -l)
RESPONSE=$(rg "Response\.assemble" src/ --type java 2>/dev/null | wc -l)
ENABLE=$(rg "@EnableExperienceAPI" src/ --type java 2>/dev/null | wc -l)

TOTAL=$((FILTER + CONTEXT + EXCEPT + RESPONSE + ENABLE))

echo "Filters: $FILTER | Context: $CONTEXT | Exceptions: $EXCEPT | Responses: $RESPONSE | Enable: $ENABLE"
echo "Integration Score: $TOTAL / 50"

if [ $ENABLE -eq 0 ]; then
  echo "⚠️  EPS Not Enabled - Install @EnableExperienceAPI"
elif [ $TOTAL -lt 20 ]; then
  echo "⚠️  Limited Integration - Add more MCA2 frameworks"
elif [ $TOTAL -lt 40 ]; then
  echo "✅ Good Integration"
else
  echo "✅✅✅ Excellent Integration"
fi
```

---

## Full Detection Report Generator

```bash
#!/bin/bash
# save as eps-detection-report.sh
# Usage: bash eps-detection-report.sh [output_file.txt]

OUTPUT_FILE="${1:-eps-detection-report.txt}"

echo "=== MCA2 EPS Framework Detection Report ===" | tee "$OUTPUT_FILE"
echo "Generated: $(date)" | tee -a "$OUTPUT_FILE"
echo "Repository: $(pwd)" | tee -a "$OUTPUT_FILE"
echo | tee -a "$OUTPUT_FILE"

# FILTER CHAIN SECTION
echo "==== FILTER CHAIN ANALYSIS ====" | tee -a "$OUTPUT_FILE"
FILTER_COUNT=$(rg "extends OncePerRequestFilter" src/ --type java 2>/dev/null | wc -l)
DOFILTER_COUNT=$(rg "filterChain\.doFilter\(" src/ --type java 2>/dev/null | wc -l)
REGISTRATION_COUNT=$(rg "FilterRegistrationBean<" src/ --type java 2>/dev/null | wc -l)

echo "Filter implementations: $FILTER_COUNT" | tee -a "$OUTPUT_FILE"
echo "Chain passes (doFilter calls): $DOFILTER_COUNT" | tee -a "$OUTPUT_FILE"
echo "Filter registrations: $REGISTRATION_COUNT" | tee -a "$OUTPUT_FILE"

if [ "$FILTER_COUNT" -eq "$DOFILTER_COUNT" ]; then
  echo "✅ All filters properly call doFilter()" | tee -a "$OUTPUT_FILE"
else
  echo "⚠️  Some filters may not call doFilter()" | tee -a "$OUTPUT_FILE"
fi
echo | tee -a "$OUTPUT_FILE"

# CONTEXT SYSTEM SECTION
echo "==== CONTEXT SYSTEM ANALYSIS ====" | tee -a "$OUTPUT_FILE"
IOL_USAGE=$(rg "IOLSchema" src/ --type java 2>/dev/null | wc -l)
CONTEXT_INJECT=$(rg "@IOLContext" src/ --type java 2>/dev/null | wc -l)
WEBUTILS_ACCESS=$(rg "WebUtils\.get.*Context" src/ --type java 2>/dev/null | wc -l)

echo "IOLSchema references: $IOL_USAGE" | tee -a "$OUTPUT_FILE"
echo "@IOLContext injections: $CONTEXT_INJECT" | tee -a "$OUTPUT_FILE"
echo "WebUtils context access: $WEBUTILS_ACCESS" | tee -a "$OUTPUT_FILE"

if [ "$CONTEXT_INJECT" -ge 1 ]; then
  echo "✅ Context system in use" | tee -a "$OUTPUT_FILE"
else
  echo "⚠️  No @IOLContext usage found" | tee -a "$OUTPUT_FILE"
fi
echo | tee -a "$OUTPUT_FILE"

# EXCEPTION HANDLING SECTION
echo "==== EXCEPTION HANDLING ANALYSIS ====" | tee -a "$OUTPUT_FILE"
EXCEPTION_TYPES=$(rg "extends GenericException" src/ --type java 2>/dev/null | wc -l)
EXCEPTION_THROWS=$(rg "throw new.*Exception" src/ --type java 2>/dev/null | wc -l)
EXCEPTION_HANDLERS=$(rg "catch.*GenericException" src/ --type java 2>/dev/null | wc -l)

echo "Exception types defined: $EXCEPTION_TYPES" | tee -a "$OUTPUT_FILE"
echo "Exception throws: $EXCEPTION_THROWS" | tee -a "$OUTPUT_FILE"
echo "Exception handlers: $EXCEPTION_HANDLERS" | tee -a "$OUTPUT_FILE"

if [ "$EXCEPTION_TYPES" -ge 5 ]; then
  echo "✅ Comprehensive exception hierarchy" | tee -a "$OUTPUT_FILE"
else
  echo "⚠️  Limited exception types" | tee -a "$OUTPUT_FILE"
fi
echo | tee -a "$OUTPUT_FILE"

# RESPONSE HANDLING SECTION
echo "==== RESPONSE HANDLING ANALYSIS ====" | tee -a "$OUTPUT_FILE"
RESPONSE_ASSEMBLE=$(rg "Response\.assemble" src/ --type java 2>/dev/null | wc -l)
RESPONSE_BUILD=$(rg "\.build\(" src/ --type java 2>/dev/null | wc -l)
RESPONSE_ENTITY=$(rg "ResponseEntity<Response" src/ --type java 2>/dev/null | wc -l)

echo "Response.assemble() calls: $RESPONSE_ASSEMBLE" | tee -a "$OUTPUT_FILE"
echo "Response builds: $RESPONSE_BUILD" | tee -a "$OUTPUT_FILE"
echo "ResponseEntity<Response> usage: $RESPONSE_ENTITY" | tee -a "$OUTPUT_FILE"

if [ "$RESPONSE_ASSEMBLE" -ge 5 ]; then
  echo "✅ Good response envelope usage" | tee -a "$OUTPUT_FILE"
else
  echo "⚠️  Limited response envelope usage" | tee -a "$OUTPUT_FILE"
fi
echo | tee -a "$OUTPUT_FILE"

# FRAMEWORK ENABLEMENT SECTION
echo "==== FRAMEWORK ENABLEMENT ANALYSIS ====" | tee -a "$OUTPUT_FILE"
ENABLE_EPS=$(rg "@EnableExperienceAPI" src/ --type java 2>/dev/null | wc -l)
ENABLE_OPTIONAL=$(rg "@Enable(SecureProxy|Router|Masking)" src/ --type java 2>/dev/null | wc -l)

echo "@EnableExperienceAPI: $ENABLE_EPS" | tee -a "$OUTPUT_FILE"
echo "Optional enables: $ENABLE_OPTIONAL" | tee -a "$OUTPUT_FILE"

if [ "$ENABLE_EPS" -eq 1 ]; then
  echo "✅ Framework properly enabled" | tee -a "$OUTPUT_FILE"
else
  echo "❌ Framework not properly enabled" | tee -a "$OUTPUT_FILE"
fi
echo | tee -a "$OUTPUT_FILE"

# CONFIGURATION SECTION
echo "==== CONFIGURATION ANALYSIS ====" | tee -a "$OUTPUT_FILE"
CONFIG_FILES=$(find src/ -name "application*.properties" 2>/dev/null | wc -l)
EPS_PROPERTIES=$(grep -r "mca\.eps\|masking\.enabled" src/ 2>/dev/null | wc -l)

echo "Property files: $CONFIG_FILES" | tee -a "$OUTPUT_FILE"
echo "MCA2 properties configured: $EPS_PROPERTIES" | tee -a "$OUTPUT_FILE"

if [ "$CONFIG_FILES" -ge 1 ]; then
  echo "✅ Configuration present" | tee -a "$OUTPUT_FILE"
else
  echo "⚠️  No configuration files found" | tee -a "$OUTPUT_FILE"
fi
echo | tee -a "$OUTPUT_FILE"

# OVERALL SCORE
echo "==== OVERALL INTEGRATION SCORE ====" | tee -a "$OUTPUT_FILE"
TOTAL=$((FILTER_COUNT + CONTEXT_INJECT + EXCEPTION_TYPES + RESPONSE_ASSEMBLE + ENABLE_EPS))
echo "Total integration score: $TOTAL / 50" | tee -a "$OUTPUT_FILE"

if [ $TOTAL -lt 10 ]; then
  LEVEL="⚠️  MINIMAL"
elif [ $TOTAL -lt 20 ]; then
  LEVEL="⚠️  BASIC"
elif [ $TOTAL -lt 30 ]; then
  LEVEL="✅ GOOD"
elif [ $TOTAL -lt 40 ]; then
  LEVEL="✅✅ STRONG"
else
  LEVEL="✅✅✅ EXCELLENT"
fi

echo "Integration Level: $LEVEL" | tee -a "$OUTPUT_FILE"
echo | tee -a "$OUTPUT_FILE"
echo "Report saved to: $OUTPUT_FILE"
```

**Run it:**
```bash
bash eps-detection-report.sh
cat eps-detection-report.txt
```

---

## Python Detection Tool

```python
#!/usr/bin/env python3
# save as eps_detector.py

import subprocess
import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DetectionResult:
    category: str
    pattern: str
    count: int
    expected: str
    status: str

class EPSDetector:
    def __init__(self, root_path="."):
        self.root_path = Path(root_path)
        self.results = []

    def run_rg(self, pattern):
        """Run ripgrep pattern search"""
        try:
            result = subprocess.run(
                ["rg", pattern, str(self.root_path), "--type", "java"],
                capture_output=True,
                text=True
            )
            return len([l for l in result.stdout.split("\n") if l.strip()])
        except:
            return 0

    def analyze(self):
        """Run full analysis"""

        # Filter chain
        self._detect("FILTER_CHAIN", "extends OncePerRequestFilter", "3-5")
        self._detect("FILTER_CHAIN", "filterChain\\.doFilter\\(", "3+")

        # Context system
        self._detect("CONTEXT", "@IOLContext", "3+")
        self._detect("CONTEXT", "WebUtils\\.get.*Context", "0+")

        # Exceptions
        self._detect("EXCEPTIONS", "extends GenericException", "5")
        self._detect("EXCEPTIONS", "throw new.*Exception", "10+")

        # Responses
        self._detect("RESPONSES", "Response\\.assemble", "10+")
        self._detect("RESPONSES", "ResponseEntity<Response", "5+")

        # Enablement
        self._detect("ENABLEMENT", "@EnableExperienceAPI", "1")
        self._detect("ENABLEMENT", "@Enable(SecureProxy|Router|Masking)", "0+")

    def _detect(self, category, pattern, expected):
        count = self.run_rg(pattern)
        status = "✅" if count > 0 else "❌"

        self.results.append(
            DetectionResult(category, pattern, count, expected, status)
        )

    def report(self):
        """Generate report"""
        print("\n=== MCA2 EPS Framework Detection Report ===\n")

        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)

        total_score = 0
        for category, results in by_category.items():
            print(f"\n{category}:")
            for result in results:
                print(f"  {result.status} {result.pattern}: {result.count} (expect: {result.expected})")
                total_score += result.count

        print(f"\n{'='*40}")
        print(f"OVERALL SCORE: {total_score} / 50")

        if total_score < 10:
            level = "⚠️  MINIMAL"
        elif total_score < 20:
            level = "⚠️  BASIC"
        elif total_score < 30:
            level = "✅ GOOD"
        elif total_score < 40:
            level = "✅✅ STRONG"
        else:
            level = "✅✅✅ EXCELLENT"

        print(f"LEVEL: {level}")

if __name__ == "__main__":
    detector = EPSDetector(".")
    detector.analyze()
    detector.report()
```

**Run it:**
```bash
python3 eps_detector.py
```

---

## GitHub Actions CI/CD Integration

```yaml
# .github/workflows/eps-detection.yml

name: MCA2 EPS Framework Detection

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  detect:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Install ripgrep
      run: sudo apt-get install -y ripgrep

    - name: Run EPS Detection
      run: |
        echo "=== MCA2 EPS Framework Detection ===" >> $GITHUB_STEP_SUMMARY
        echo "" >> $GITHUB_STEP_SUMMARY

        echo "Filter Chain:" >> $GITHUB_STEP_SUMMARY
        echo "- Filters: $(rg 'extends OncePerRequestFilter' src/ --type java | wc -l)" >> $GITHUB_STEP_SUMMARY
        echo "- Chain calls: $(rg 'filterChain\.doFilter\(' src/ --type java | wc -l)" >> $GITHUB_STEP_SUMMARY

        echo "Context System:" >> $GITHUB_STEP_SUMMARY
        echo "- @IOLContext: $(rg '@IOLContext' src/ --type java | wc -l)" >> $GITHUB_STEP_SUMMARY

        echo "Exceptions:" >> $GITHUB_STEP_SUMMARY
        echo "- Types: $(rg 'extends GenericException' src/ --type java | wc -l)" >> $GITHUB_STEP_SUMMARY

        echo "Responses:" >> $GITHUB_STEP_SUMMARY
        echo "- Response.assemble: $(rg 'Response\.assemble' src/ --type java | wc -l)" >> $GITHUB_STEP_SUMMARY

        echo "Enablement:" >> $GITHUB_STEP_SUMMARY
        echo "- @EnableExperienceAPI: $(rg '@EnableExperienceAPI' src/ --type java | wc -l)" >> $GITHUB_STEP_SUMMARY

    - name: Check Framework Integration
      run: |
        ENABLE=$(rg '@EnableExperienceAPI' src/ --type java | wc -l)

        if [ "$ENABLE" -eq 0 ]; then
          echo "❌ @EnableExperienceAPI not found"
          exit 1
        fi

        echo "✅ Framework properly enabled"
```

---

## GitLab CI Integration

```yaml
# .gitlab-ci.yml

eps-detection:
  stage: analyze
  image: ubuntu:latest
  script:
    - apt-get update && apt-get install -y ripgrep
    - |
      echo "=== MCA2 EPS Detection Report ===" > eps-report.txt
      echo "Filters: $(rg 'extends OncePerRequestFilter' src/ --type java | wc -l)" >> eps-report.txt
      echo "Context: $(rg '@IOLContext' src/ --type java | wc -l)" >> eps-report.txt
      echo "Exceptions: $(rg 'extends GenericException' src/ --type java | wc -l)" >> eps-report.txt
      echo "Responses: $(rg 'Response\.assemble' src/ --type java | wc -l)" >> eps-report.txt
      echo "Enabled: $(rg '@EnableExperienceAPI' src/ --type java | wc -l)" >> eps-report.txt
    - cat eps-report.txt
  artifacts:
    reports:
      dotenv: eps-report.txt
```

---

## Jenkins Integration

```groovy
// Jenkinsfile

pipeline {
    agent any

    stages {
        stage('EPS Detection') {
            steps {
                script {
                    sh '''
                        echo "=== MCA2 EPS Framework Detection ===" > eps-detection.log

                        FILTERS=$(rg "extends OncePerRequestFilter" src/ --type java | wc -l)
                        CONTEXT=$(rg "@IOLContext" src/ --type java | wc -l)
                        EXCEPT=$(rg "extends GenericException" src/ --type java | wc -l)
                        RESPONSE=$(rg "Response\\.assemble" src/ --type java | wc -l)
                        ENABLE=$(rg "@EnableExperienceAPI" src/ --type java | wc -l)

                        TOTAL=$((FILTERS + CONTEXT + EXCEPT + RESPONSE + ENABLE))

                        echo "Framework Integration Score: $TOTAL / 50" >> eps-detection.log

                        if [ "$ENABLE" -eq 0 ]; then
                            echo "ERROR: Framework not enabled" >> eps-detection.log
                            exit 1
                        fi

                        cat eps-detection.log
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'eps-detection.log'
        }
    }
}
```

---

## Docker Integration

```dockerfile
# Dockerfile.detection

FROM ubuntu:latest

RUN apt-get update && apt-get install -y ripgrep

COPY . /workspace
WORKDIR /workspace

RUN echo "=== MCA2 EPS Detection ===" && \
    echo "Filters: $(rg 'extends OncePerRequestFilter' src/ --type java | wc -l)" && \
    echo "Context: $(rg '@IOLContext' src/ --type java | wc -l)" && \
    echo "Exceptions: $(rg 'extends GenericException' src/ --type java | wc -l)" && \
    echo "Responses: $(rg 'Response\.assemble' src/ --type java | wc -l)" && \
    echo "Enabled: $(rg '@EnableExperienceAPI' src/ --type java | wc -l)"
```

**Run it:**
```bash
docker build -f Dockerfile.detection -t eps-detector .
docker run eps-detector
```

---

## Reporting Best Practices

### Include in Report
- ✅ Integration score (0-50)
- ✅ Count for each category
- ✅ Missing patterns
- ✅ Recommendations for improvement
- ✅ Timestamp and repository info

### Present Findings
- Show data in table format
- Use visual indicators (✅, ⚠️, ❌)
- Compare to expected values
- Highlight critical issues (not enabled)

### Act on Results
- Score < 10: "Not using MCA2"
- Score 10-20: "Recommend framework integration"
- Score 20-30: "Good, consider expanding"
- Score 30+: "Excellent integration"

---

## Next Steps

1. **Run Quick Detection** — Use 30-second script
2. **Generate Full Report** — Use full script or Python tool
3. **Integrate with CI/CD** — Add GitHub Actions/GitLab/Jenkins step
4. **Schedule Regularly** — Weekly/monthly automated scans
5. **Track Trend** — Monitor integration score over time

**Detection Runner enables automated MCA2 framework analysis.**
