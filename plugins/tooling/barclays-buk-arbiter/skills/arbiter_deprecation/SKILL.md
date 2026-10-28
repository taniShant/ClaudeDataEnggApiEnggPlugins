---
user-invocable: false
description: "Public API deprecation management strategy, consultation workflow, migration path documentation"
---

# Skill: Deprecation Management

## Source Attribution

**Source:** Best practices for API deprecation (Java @Deprecated annotation, semantic versioning standards, and industry migration patterns).  
**Owner:** Preetha Ramaswamy  
**Review trigger:** On Arbiter version major/minor release, or when deprecation consultation workflow changes.

## Agent Self-Check

- [ ] @Deprecated detection: Identifies all methods/classes marked @Deprecated
- [ ] Deprecation date extraction: Parses `since` and `forRemoval` attributes
- [ ] Migration path documentation: Checks for JavaDoc references to replacement APIs
- [ ] Consultation workflow: Batches deprecated code by risk level
- [ ] Timeline calculation: Determines when safe to remove

---

## Deprecation Categorization

| Category | Age | Replacement | Usage | Action |
|----------|-----|-------------|-------|--------|
| **Safe to Remove** | >1 year | Clear replacement | 0 usages | Remove directly |
| **Needs Testing** | 6-12 months | Migration path exists | <5 usages | Test + review |
| **Requires Approval** | <6 months | Unclear path | 5+ usages | Consult team |
| **Keep** | <3 months | N/A | Any | Wait longer |

---

## @Deprecated Annotation Fields

```java
@Deprecated(since = "2.0", forRemoval = true, 
    message = "Use newMethod() instead")
public void oldMethod() { ... }
```

**Extract:**
- `since`: Version when deprecated (e.g., "2.0")
- `forRemoval`: Boolean; true = planned for removal
- Message: Often contains replacement method name

---

## Confidence Boost for @Deprecated

| Attribute | Boost |
|-----------|-------|
| `@Deprecated` present | +0.5 |
| `forRemoval = true` | +0.3 |
| `since` >1 year old | +0.2 |
| Replacement documented | +0.3 |
| No external usage | +0.5 |

**Example:**
```
Base confidence: 3.0
@Deprecated (+0.5) + forRemoval (+0.3) + 2 years old (+0.2) + no usage (+0.5)
= 4.5 → clamped to 4.0 (SAFE)
```

---

## Migration Path Extraction

**Look for in JavaDoc:**
```
/**
 * @deprecated Use {@link NewClass#newMethod()} instead.
 * Migration guide: ...
 */
@Deprecated
public void oldMethod() { ... }
```

**Extract:**
- Replacement class/method (e.g., `NewClass#newMethod()`)
- Migration guide URL/documentation
- Suggested version to upgrade to

---

## Consultation Workflow

### Step 1: Batch @Deprecated Entities

```
[T-SAFE]     → @Deprecated 2+ years, no usage, clear replacement
[T-REVIEW]   → @Deprecated 6-12 months, <5 usages, needs testing
[T-CONSULT]  → @Deprecated <6 months OR 5+ usages OR unclear replacement
```

### Step 2: Engineer Consultation

For [T-CONSULT] batch:

**Questions to ask:**
1. "Is this safe to remove in next version?"
2. "What is the migration path for existing users?"
3. "When can we officially remove this?"
4. "Are there external consumers we should notify?"

**Document:**
- Engineer decision (remove / keep)
- Reason (timeline / dependency / migration)
- Next steps (notify users / update docs)

### Step 3: Batch Execution

- **[T-SAFE]:** Execute with SAFE gates (compile + unit)
- **[T-REVIEW]:** Execute with LIKELY gates (integration tests required)
- **[T-CONSULT]:** Only execute after engineer approval

---

## Timeline Recommendations

| Time Since Deprecation | Recommendation |
|---|---|
| **<3 months** | Do not remove; too early |
| **3-6 months** | Consult engineer; may remove with approval |
| **6-12 months** | Review usage; plan removal in next version |
| **12+ months** | Safe to remove; low external dependency risk |

---

## Documentation Checklist

Before removing deprecated code:

- [ ] Replacement method clearly documented
- [ ] Migration guide provided (if applicable)
- [ ] Users/consumers notified (external APIs)
- [ ] Deprecation period respected (≥6 months)
- [ ] All usages within repo refactored
- [ ] Release notes updated

---

## False Positives

| Pattern | Risk | Mitigation |
|---------|------|-----------|
| **Public API** | Removed without external notification | Document deprecation period; notify consumers |
| **Framework deprecated** | Framework removes dependency; breaks app | Check framework version requirements |
| **Conditional removal** | Code conditionally compiled/used | Lower confidence; investigate |

---

## Examples

### Example 1: Safe Deprecation (3 years old)

```java
/**
 * @deprecated since 1.0, forRemoval = true
 * Use {@link UserService#getUser(long)} instead.
 */
@Deprecated(since = "1.0", forRemoval = true)
public User fetchUser(String userId) { ... }
```

**Analysis:**
- Age: 3 years
- Replacement: Clear (UserService#getUser)
- Usage: 0 in codebase
- Confidence: 4.0 (SAFE)
- Action: Remove directly

### Example 2: Risky Deprecation (3 months old)

```java
/**
 * @deprecated Use ConfigBuilder instead
 */
@Deprecated
public Config newConfig() { ... }
```

**Analysis:**
- Age: 3 months
- Replacement: Vague ("ConfigBuilder")
- Usage: 12 calls in codebase
- Confidence: 1.5 (UNCERTAIN)
- Action: Consult engineer; too early to remove

---

## Removal Checklist for Deprecated Code

- [ ] `forRemoval = true` present
- [ ] Deprecation age ≥6 months
- [ ] Migration path documented
- [ ] All usages in repo refactored to replacement
- [ ] External consumers notified (if public API)
- [ ] Release notes prepared
- [ ] Engineering approval obtained (if <12 months)

---

## Semantic Versioning Impact

| Version Change | Removal Impact |
|---|---|
| **Major (1.0 → 2.0)** | OK to remove deprecated; breaking change expected |
| **Minor (1.0 → 1.1)** | Not OK to remove; keep deprecated |
| **Patch (1.0 → 1.0.1)** | Never remove; bugfix only |

**Recommendation:** Coordinate removal with major version release.

---

## Notes

- **Conservative:** When in doubt, keep deprecated code longer
- **Communication:** Notify users before removing public APIs
- **Versioning:** Align deprecation removal with semantic versioning releases
- **Testing:** All removal should pass comprehensive tests
