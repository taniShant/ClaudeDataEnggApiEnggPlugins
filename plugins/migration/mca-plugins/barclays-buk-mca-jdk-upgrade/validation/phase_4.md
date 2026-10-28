# Phase 4 Validation Checklist

Post-Phase 4 verification checks. Run after Phase 4 commit to confirm Java 8→21 code changes were applied.

## Checks

### Check 1: No Deprecated/Removed Java APIs

**What**: Code doesn't use APIs that were removed in Java 9-21.

**How to verify**:
```bash
# Check for removed Thread methods
if grep -rnE "Thread\.(stop|suspend|resume)\(" --include="*.java" src/ 2>/dev/null; then
  echo "FAIL: Removed Thread methods still in use"
else
  echo "PASS: No removed Thread methods"
fi

# Check for Runtime.runFinalizersOnExit
if grep -rn "runFinalizersOnExit" --include="*.java" src/ 2>/dev/null; then
  echo "FAIL: Runtime.runFinalizersOnExit still in use (removed in Java 11)"
else
  echo "PASS: No runFinalizersOnExit usage"
fi

# Check for SecurityManager usage
if grep -rnE "new SecurityManager|System\.(set|get)SecurityManager" --include="*.java" src/ 2>/dev/null; then
  echo "WARN: SecurityManager usage detected (deprecated for removal)"
fi
```

**On failure**: Agent must refactor to use alternative APIs per Java 21 migration guides.

### Check 2: JAXB Dependencies Present (if XML binding used)

**What**: If project uses JAXB annotations, jakarta.xml.bind dependencies are present.

**How to verify**:
```bash
# Check if code uses JAXB annotations
if grep -rnE "@XmlRootElement|@XmlElement|JAXBContext" --include="*.java" src/ 2>/dev/null | grep -v "^Binary" | wc -l | grep -qv "^0$"; then
  # JAXB usage detected, check dependencies
  if grep -qE "jakarta\.xml\.bind|jaxb-api" build.gradle 2>/dev/null; then
    echo "PASS: JAXB dependencies present"
  else
    echo "FAIL: JAXB usage detected but no jakarta.xml.bind dependency"
  fi
else
  echo "PASS: No JAXB usage detected"
fi
```

**On failure**: Agent must add `jakarta.xml.bind:jakarta.xml.bind-api` and runtime implementation.

### Check 3: --add-opens for Reflection (if Spring/Hibernate)

**What**: JVM args include --add-opens for packages that Spring/Hibernate need to access via reflection.

**How to verify**:
```bash
if grep -qE "spring|hibernate" build.gradle 2>/dev/null; then
  if grep -qE "add-opens.*(java\.base/java\.lang|java\.base/java\.lang\.reflect)" build.gradle 2>/dev/null; then
    echo "PASS: --add-opens present for Spring/Hibernate"
  else
    echo "WARN: Spring/Hibernate detected but no --add-opens args (may cause reflection errors)"
  fi
else
  echo "SKIP: No Spring/Hibernate detected"
fi
```

**On failure**: Agent should add --add-opens args to applicationDefaultJvmArgs or test JVM args.

### Check 4: Spring Security Migration (if applicable)

**What**: Spring Security 6+ patterns used instead of deprecated WebSecurityConfigurerAdapter.

**How to verify**:
```bash
if grep -rn "WebSecurityConfigurerAdapter" --include="*.java" src/ 2>/dev/null | grep -v "^Binary"; then
  echo "FAIL: WebSecurityConfigurerAdapter still in use (removed in Spring Security 6)"
else
  if grep -qE "spring-boot-starter-security|spring-security" build.gradle 2>/dev/null; then
    echo "PASS: Spring Security migration complete or not applicable"
  else
    echo "SKIP: No Spring Security detected"
  fi
fi
```

**On failure**: Agent must refactor to use SecurityFilterChain bean pattern.

### Check 5: Jackson JSR-310 Support (if java.time used)

**What**: If code uses java.time classes (LocalDate, ZonedDateTime, etc.), jackson-datatype-jsr310 dependency is present.

**How to verify**:
```bash
if grep -rnE "import java\.time\." --include="*.java" src/ 2>/dev/null | grep -v "^Binary" | wc -l | grep -qv "^0$"; then
  if grep -q "jackson-datatype-jsr310" build.gradle 2>/dev/null; then
    echo "PASS: Jackson JSR-310 support present"
  else
    echo "WARN: java.time usage detected but no jackson-datatype-jsr310 (may cause serialization errors)"
  fi
else
  echo "SKIP: No java.time usage detected"
fi
```

**On failure**: Agent should add jackson-datatype-jsr310 dependency.

### Check 6: Dockerfile Java Version (if present)

**What**: If Dockerfile exists, base image uses Java 21 (not Java 8).

**How to verify**:
```bash
if [ -f "Dockerfile" ]; then
  if grep -qE "FROM.*java.*:8|FROM.*jdk.*:8|FROM.*openjdk:8" Dockerfile; then
    echo "FAIL: Dockerfile still uses Java 8 base image"
  elif grep -qE "FROM.*java.*:21|FROM.*jdk.*:21|FROM.*openjdk:21" Dockerfile; then
    echo "PASS: Dockerfile uses Java 21 base image"
  else
    echo "WARN: Dockerfile Java version unclear"
  fi
else
  echo "SKIP: No Dockerfile present"
fi
```

**On failure**: Agent must update Dockerfile FROM statement to Java 21 base image.

### Check 7: Project Compiles

**What**: Project compiles successfully after all Java 8→21 code changes.

**How to verify**:
```bash
$GRADLE_CMD compileJava > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "PASS: compileJava succeeded"
else
  echo "FAIL: compileJava failed after Phase 4"
fi
```

**On failure**: This is BLOCKING. Agent must investigate and fix compilation errors.

## Integration

These checks validate that Phase 4's Java language-level changes were applied correctly. Most checks are conditional (only run if the feature is detected in the codebase).
