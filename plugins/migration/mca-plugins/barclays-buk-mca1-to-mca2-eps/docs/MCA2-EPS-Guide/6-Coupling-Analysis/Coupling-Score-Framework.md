# Coupling Score Framework: 5-Tier Integration Metrics

## Executive Summary

The **Coupling Score Framework** provides a quantitative measure of how deeply an application integrates with MCA2 EPS framework. Scores range from 0-50+ across five tiers, enabling standardized architecture assessment and integration tracking.

**Scoring Formula:**
```
Score = (CoreModules × 3) + (FrameworkModules × 2) + (OptionalModules × 1)
        + LayeringBonus + ConditionalBonus
```

---

## Core Components: Weight Assignments

### Tier 1: Core Modules (Weight: 3)
**Foundation modules used in all EPS applications.**

| Module | Points | Presence | Check |
|--------|--------|----------|-------|
| mca-context | +3 | Dependency | grep IOLSchema |
| mca-context-utils | +3 | Dependency | grep context.utils |
| mca-filter-core | +3 | Filters extending OncePerRequestFilter | rg "extends OncePerRequestFilter" |
| mca-eps-core | +3 | @EnableExperienceAPI | rg "@EnableExperienceAPI" |
| mca-exception-handling-core | +3 | throw GenericException | rg "extends GenericException" |
| mca-response-handling-core | +3 | Response.assemble() | rg "Response\.assemble" |
| mca-logging-aspects | +3 | Logger usage | rg "LoggerFactory" |

**Subtotal if all present: 21 points**

### Tier 2: Framework Modules (Weight: 2)
**Major optional frameworks enhancing core EPS.**

| Module | Points | Presence | Check |
|--------|--------|----------|-------|
| mca-masking | +2 | @Masked annotations | rg "@Masked\|masking\.patterns" |
| mca-service-client-starter | +2 | RestClientFactory | rg "RestClientFactory" |
| mca-router-http | +2 | @EnableRouter | rg "@EnableRouter" |
| mca-secure-proxy-core | +2 | @EnableSecureProxy | rg "@EnableSecureProxy" |
| mca-placeholder-starter | +2 | Property resolution | rg "PropertyPlaceholder" |
| mca-oauth-validator-core | +2 | OAuth filter | rg "OAuthValidator" |

**Note:** Context store modules (mca-context-store-rdb/mongo/ehcache) are part of the Secure Proxy module, not EPS core. They are scored separately if used with Secure Proxy.

**Subtotal if all present: 12 points**

### Tier 3: Optional Integration (Weight: 1)
**Specialized modules for specific use cases.**

| Module | Points | Presence |
|--------|--------|----------|
| mca-referencedata | +1 | Reference data usage |
| mca-entitlement | +1 | Authorization checks |
| mca-sso | +1 | SSO integration |
| bem-client, mis-client | +1 | Legacy integration |
| spring-boot-ssl | +1 | SSL configuration |

**Subtotal if all present: 5 points**

---

## Bonus Points: Quality Factors

### Layering Bonus (-1 per layer)
Reward proper API→Core→Starter layering:

```
Correct layering detected:
  ├─ Module has -api variant
  ├─ Module has -core implementation
  └─ Module has -starter auto-config
  → -1 point per properly-layered module
  → Maximum: -5 points (all 5 major frameworks)
```

**Detection:**
```bash
# Count properly-layered modules
find . -name "*-api" -o -name "*-core" -o -name "*-starter" | \
  sed 's/-api\|-core\|-starter//' | sort | uniq -c | grep "3$" | wc -l
```

### Conditional Enablement Bonus (-0.5 per toggle)
Reward feature toggles via @ConditionalOnProperty:

```bash
# Count conditional beans
rg "@ConditionalOnProperty" src/ --type java | wc -l
# Multiply by 0.5: result ÷ 2
# Maximum: -2.5 points (5 feature toggles)
```

---

## 5-Tier Classification System

### Tier 1: Minimal Integration (Score: 0-3)

**Characteristics:**
- No @EnableExperienceAPI
- At most 1 core framework
- No context injection
- Minimal exception handling

**Example:**
```
Application: Single service, just logging
Score: 3 points
  - mca-logging-aspects: 3 points
```

**Status:** ❌ Not using MCA2 EPS

**Recommendation:**
- Add @EnableExperienceAPI
- Enable context system
- Use Response<T> envelope

---

### Tier 2: Basic Integration (Score: 4-8)

**Characteristics:**
- @EnableExperienceAPI present
- Context system enabled
- Basic exception handling
- Limited response envelope usage

**Example:**
```
Application: REST API with basic EPS
Score: 7 points
  - mca-context: 3
  - mca-eps-core: 3
  - @EnableExperienceAPI: 1
```

**Status:** ⚠️ Core EPS only

**Recommendation:**
- Add Response<T> everywhere
- Add masking

---

### Tier 3: Core Integration (Score: 9-15)

**Characteristics:**
- All core modules present (21 baseline)
- Consistent Response envelope (+3)
- Good exception usage (+2)
- Some feature toggles (-0.5)

**Formula:**
```
21 (core modules)
- 0.5 (conditional toggles)
= 20.5 → rounds to 15-16 range
```

**Example:**
```
Application: Full EPS framework
Score: 13 points
  - Core modules: 21 baseline
  - Layering bonus: -1
  - Conditional toggles: -2
  = 18 base → normalized to 13-15 range
```

**Status:** ✅ Good integration

**Recommendation:**
- Add service client framework
- Enable routing if needed
- Consider proxy framework

---

### Tier 4: Heavy Integration (Score: 16-25)

**Characteristics:**
- All core modules (21)
- Multiple framework modules (+6-8)
- Proper layering (-2)
- Feature toggles (-2)
- Specialized integrations (+1-2)

**Formula:**
```
21 (core)
+ 8 (frameworks: masking, router, proxy, service-client, oauth)
- 2 (layering)
- 2 (conditionals)
+ 2 (specializations)
= 25
```

**Status:** ✅✅ Strong integration

**Recommendation:**
- Monitor coupling complexity
- Document integration points
- Plan maintenance strategy

---

### Tier 5: Full Platform Integration (Score: 26+)

**Characteristics:**
- All tiers 1-3 fully populated
- All optional frameworks (+14 baseline)
- Proper layering throughout (-3 to -5)
- Extensive feature toggles (-3 to -5)
- Complete specialization (+3-5)

**Formula:**
```
21 (core)
+ 14 (all frameworks)
- 4 (comprehensive layering)
- 4 (multiple conditionals)
+ 4 (specializations)
= 31+
```

**Example Production System:**
```
Score: 35+ points
- Core modules: 21
- All framework modules: 14
- Proper layering: -4
- Feature toggles: -3
- Specialized integrations: +4
- API → Core → Starter everywhere: yes
- Custom filters with ordering: yes
- Comprehensive masking: yes
```

**Status:** ✅✅✅ Excellent integration

**Notes:**
- Full framework adoption
- Enterprise-grade integration
- High maintainability
- All benefits realized

---

## Scoring Calculation: Step-by-Step

### Step 1: Count Core Modules

```bash
CORE_SCORE=0

# Check each core module
[ "$(rg 'IOLSchema' src/ --type java | wc -l)" -gt 0 ] && CORE_SCORE=$((CORE_SCORE + 3))
[ "$(rg 'extends OncePerRequestFilter' src/ --type java | wc -l)" -gt 0 ] && CORE_SCORE=$((CORE_SCORE + 3))
[ "$(rg '@EnableExperienceAPI' src/ --type java | wc -l)" -gt 0 ] && CORE_SCORE=$((CORE_SCORE + 3))
[ "$(rg 'extends GenericException' src/ --type java | wc -l)" -gt 0 ] && CORE_SCORE=$((CORE_SCORE + 3))
[ "$(rg 'Response\.assemble' src/ --type java | wc -l)" -gt 0 ] && CORE_SCORE=$((CORE_SCORE + 3))
[ "$(rg 'LoggerFactory' src/ --type java | wc -l)" -gt 0 ] && CORE_SCORE=$((CORE_SCORE + 3))

echo "Core Score: $CORE_SCORE / 21"
```

### Step 2: Count Framework Modules

```bash
FRAMEWORK_SCORE=0

# Check each framework module
[ "$(rg '@Masked|masking\.patterns' src/ --type java | wc -l)" -gt 0 ] && FRAMEWORK_SCORE=$((FRAMEWORK_SCORE + 2))
[ "$(rg 'RestClientFactory' src/ --type java | wc -l)" -gt 0 ] && FRAMEWORK_SCORE=$((FRAMEWORK_SCORE + 2))
[ "$(rg '@EnableRouter' src/ --type java | wc -l)" -gt 0 ] && FRAMEWORK_SCORE=$((FRAMEWORK_SCORE + 2))
[ "$(rg '@EnableSecureProxy' src/ --type java | wc -l)" -gt 0 ] && FRAMEWORK_SCORE=$((FRAMEWORK_SCORE + 2))

echo "Framework Score: $FRAMEWORK_SCORE / 14"
```

### Step 3: Calculate Bonuses

```bash
LAYERING_BONUS=0
CONDITIONAL_BONUS=0

# Layering bonus
LAYERED_MODULES=$(find . -name "*-api" -o -name "*-core" -o -name "*-starter" | \
  sed 's/-api\|-core\|-starter//' | sort | uniq -c | grep "3$" | wc -l)
LAYERING_BONUS=$((LAYERED_MODULES * -1))

# Conditional bonus
CONDITIONALS=$(rg '@ConditionalOnProperty' src/ --type java | wc -l)
CONDITIONAL_BONUS=$((CONDITIONALS * -1 / 2))

echo "Layering Bonus: $LAYERING_BONUS"
echo "Conditional Bonus: $CONDITIONAL_BONUS"
```

### Step 4: Calculate Total

```bash
TOTAL=$((CORE_SCORE + FRAMEWORK_SCORE + LAYERING_BONUS + CONDITIONAL_BONUS))

# Classify
if [ $TOTAL -lt 4 ]; then
  TIER="Tier 1: Minimal (0-3)"
elif [ $TOTAL -lt 9 ]; then
  TIER="Tier 2: Basic (4-8)"
elif [ $TOTAL -lt 16 ]; then
  TIER="Tier 3: Core (9-15)"
elif [ $TOTAL -lt 26 ]; then
  TIER="Tier 4: Heavy (16-25)"
else
  TIER="Tier 5: Full (26+)"
fi

echo "TOTAL COUPLING SCORE: $TOTAL"
echo "CLASSIFICATION: $TIER"
```

---

## Interpreting Your Score

### Score Breakdown Table

| Score | Tier | Level | Action |
|-------|------|-------|--------|
| 0-3 | 1 | ❌ Minimal | Install EPS framework |
| 4-8 | 2 | ⚠️ Basic | Add core features |
| 9-15 | 3 | ✅ Good | Expand optional features |
| 16-25 | 4 | ✅✅ Strong | Monitor complexity |
| 26+ | 5 | ✅✅✅ Excellent | Production-ready |

### Improvement Path

```
Starting at Tier 2 (Score: 6)?
  → Add masking: +2 points → Tier 3
  → Add Response<T> everywhere: +2 points → Tier 3 (score ~12)
  → Add routing: +2 points → Tier 4
  → Add proxy: +2 points → Tier 4 (score ~18)
```

---

## Using Scores for Tracking

### Version-to-Version Comparison

```
Release 1.0:  Score 8 (Tier 2 - basic)
Release 2.0:  Score 12 (Tier 3 - good)
Release 3.0:  Score 18 (Tier 4 - strong)
Release 4.0:  Score 25 (Tier 4 - heavy)
Target:       Score 30+ (Tier 5 - full)
```

### Trend Analysis

```
Positive trend:
  Quarter 1: 5 points
  Quarter 2: 9 points (+4)
  Quarter 3: 14 points (+5)
  → Good framework adoption

Stagnant:
  Quarter 1: 12 points
  Quarter 2: 12 points (no change)
  → Not leveraging framework updates

Declining:
  Quarter 1: 15 points
  Quarter 2: 12 points (-3)
  → Lost framework usage (possible refactor)
```

---

## Scoring Reference Table

### Quick Lookup: Points per Component

| Component | Points |
|-----------|--------|
| Core module present | +3 |
| Framework module present | +2 |
| Optional module present | +1 |
| Properly layered (API/Core/Starter) | -1 |
| Feature toggle (@ConditionalOnProperty) | -0.5 |
| Custom filter with proper ordering | +1 |
| Integration test suite | +0.5 |
| Performance monitoring enabled | +0.5 |

---

## Next Steps

1. **Calculate your score** — Use Step-by-Step calculation
2. **Identify your tier** — Where does your application fit?
3. **Plan improvements** — What's needed to reach next tier?
4. **Track over time** — Monitor score in version control
5. **Use for CI/CD** — Automate score calculation

---

## Quick Reference: Scoring Formula

```
COUPLING SCORE =
  (Core Modules × 3)
  + (Framework Modules × 2)
  + (Optional Modules × 1)
  + (Layering Bonus × -1)
  + (Feature Toggles × -0.5)

Classification:
  Tier 1: 0-3 (Minimal)
  Tier 2: 4-8 (Basic)
  Tier 3: 9-15 (Good)
  Tier 4: 16-25 (Strong)
  Tier 5: 26+ (Excellent)
```

**Coupling Score Framework enables quantified architecture assessment.**
