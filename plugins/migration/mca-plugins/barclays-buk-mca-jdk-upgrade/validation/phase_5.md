# Phase 5 Validation Checklist

Post-Phase 5 verification checks. Run after Phase 5 commit to confirm Apache HttpClient migration was applied (if applicable).

**NOTE**: This phase is **CONDITIONAL** — only runs if Apache HttpClient was detected in Phase 0.

## Checks

### Check 1: No Apache HttpClient Imports

**What**: No Apache HttpClient classes remain in source code.

**How to verify**:
```bash
APACHE_HTTP_COUNT=$(grep -rnc "import org.apache.http" --include="*.java" src/ 2>/dev/null | grep -v ":0$" | wc -l)
if [ "$APACHE_HTTP_COUNT" -gt 0 ]; then
  echo "FAIL: $APACHE_HTTP_COUNT files still have org.apache.http imports"
else
  echo "PASS: No Apache HttpClient imports found"
fi
```

**On failure**: Agent must complete migration to JDK HttpClient or Spring RestClient.

### Check 2: JDK HttpClient or Spring RestClient Used

**What**: Replacement HTTP client is present (JDK HttpClient or Spring RestClient).

**How to verify**:
```bash
if grep -rnE "import java\.net\.http\.|import org\.springframework\.web\.client\.RestClient" --include="*.java" src/ 2>/dev/null | grep -v "^Binary" | wc -l | grep -qv "^0$"; then
  echo "PASS: JDK HttpClient or Spring RestClient imports found"
else
  if [ "$APACHE_HTTP_COUNT" -eq 0 ]; then
    echo "PASS: No HTTP client usage detected"
  else
    echo "FAIL: Apache HttpClient removed but no replacement client found"
  fi
fi
```

**On failure**: Agent must complete HTTP client migration.

### Check 3: Apache HttpClient Dependencies Removed

**What**: Apache HttpClient dependencies removed from build.gradle.

**How to verify**:
```bash
if grep -qE "org\.apache\.(httpcomponents|httpclient)" build.gradle 2>/dev/null; then
  echo "FAIL: Apache HttpClient dependencies still in build.gradle"
else
  echo "PASS: Apache HttpClient dependencies removed"
fi
```

**On failure**: Agent must remove httpclient, httpcore, and related Apache HTTP dependencies.

### Check 4: HttpClient Bean Configured (if using JDK HttpClient)

**What**: If using JDK HttpClient, a configured HttpClient bean exists for dependency injection.

**How to verify**:
```bash
if grep -rn "import java.net.http.HttpClient" --include="*.java" src/ 2>/dev/null | grep -v "^Binary" | wc -l | grep -qv "^0$"; then
  # Check for @Bean HttpClient
  if grep -rnE "@Bean.*HttpClient|public HttpClient http" --include="*.java" src/ 2>/dev/null | grep -v "^Binary" | wc -l | grep -qv "^0$"; then
    echo "PASS: HttpClient bean configured"
  else
    echo "WARN: JDK HttpClient used but no bean configuration found (may impact testability)"
  fi
else
  echo "SKIP: Not using JDK HttpClient"
fi
```

**On failure**: Consider adding an HttpClient bean for better testability.

### Check 5: Project Compiles

**What**: Project compiles successfully after HTTP client migration.

**How to verify**:
```bash
$GRADLE_CMD compileJava > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "PASS: compileJava succeeded"
else
  echo "FAIL: compileJava failed after Phase 5"
fi
```

**On failure**: This is BLOCKING. Agent must investigate and fix compilation errors.

## Conditional Phase

Phase 5 only runs if Apache HttpClient was detected during Phase 0 scan. If Phase 5 was skipped:
- All checks should return `SKIP: Phase 5 not applicable`
- No validation failures expected

## Integration

These checks confirm Apache HttpClient was fully migrated and no orphaned imports or dependencies remain. If Phase 5 didn't run, these checks confirm no Apache HTTP usage exists in the project.
