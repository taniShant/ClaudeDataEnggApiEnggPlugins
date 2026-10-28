---
user-invocable: false
description: "Resolves live feature-switch state to enrich dead-code confidence scores. Activates when Java code contains session.getAttribute, isFeatureSwitchOn, getBooleanProperty, or getStringProperty gate patterns, or iOS code contains BMBFeatureStatusHelper / BMBPolicyValueHelper gate patterns. Runs as Step 7b inside arbiter-discover-analyze-agent (Java) and Phase 5b inside arbiter-discover-analyze-ios-agent (iOS) after base scoring. Consults configured Confluence data sources; defaults are pre-set for BMB Gateway."
---

## Source Attribution

**Source:** Barclays Mobile Banking (BMB) Gateway feature-switch detection patterns, PAYPI-7689 analysis.  
**Owner:** Preetha Ramaswamy  
**Review trigger:** On Arbiter version major/minor release, or when BMB feature-switch patterns change.

---

# Skill: Switch-Aware Dead Code Analysis

Enrich arbiter dead code confidence scores using live feature-switch state. Standard call-graph analysis cannot see through runtime feature switches — this skill resolves switch state from configured data sources and reclassifies switch-gated code blocks accordingly.

## Agent Self-Check

**Pre-run (verify before starting):**
- [ ] Configuration loaded (`.arbiter/switch-analysis.yml` if present, else defaults)
- [ ] Cache files checked before any Confluence fetch
- [ ] Version prefix and sentinel auto-detected from data (not hardcoded)
- [ ] Technology detected (Java or iOS) — gate patterns differ; see §iOS-Specific Patterns for iOS

**During analysis:**
- [ ] Switch constants resolved via auto-discovered constants classes (not hardcoded paths)
- [ ] Per-env status resolved before matrix (GLLIVE/SLLIVE override ALL.status)
- [ ] Classification matrix applied using effective status (see `references/classification-matrix.md`)
- [ ] OFF switch treated as upcoming feature NOT dead code
- [ ] No DB entry treated as neutral — NOT a dead-code signal
- [ ] KEEP ALL verdict → boost skipped entirely (boost = 0)
- [ ] Boost value is exactly +0.5, +1.0, or +1.5 — no other values used
- [ ] Cascade checked across ALL files, not just dead class file
- [ ] Cascade in shared helpers = LIKELY not SAFE
- [ ] Git signals used as supporting evidence only — never sole basis for classification

**Post-run (verify before writing output):**
- [ ] ALL unresolved switches collected and user asked before continuing (Step 7)
- [ ] Entry point exception applied — operation dispatcher classes never fully deleted
- [ ] Output report uses config-sourced page IDs, not hardcoded values

---

## Configuration

Read `.arbiter/switch-analysis.yml` if present. If absent, use built-in defaults (pre-configured for BMB Gateway — see note below).

```yaml
# .arbiter/switch-analysis.yml — override any of these defaults
switch_data_sources:
  - name: feature_switches        # mobile/client-side feature flags
    confluence_page_id: 1703299218  # DEFAULT: BMB Function Data page
    cache_file: .arbiter/cache/function_data_confluence.json
    format: json_script_block     # JSON inside a <script> tag on the page
    status_path: ALL.status       # path to ON/OFF field per switch entry

  - name: config_properties       # server-side DB/properties config
    confluence_page_id: 1399770386  # DEFAULT: BMB Gateway Config page
    cache_file: .arbiter/cache/gateway_config.txt
    format: pipe_delimited_table  # | Env | Key | ... | Value | ...
    key_column: 2                 # 1-based column index for property key
    value_column: 7               # 1-based column index for value

cache_max_age_days: 10
stale_switch_threshold: 500       # age gap from latest version = "stale"

# iOS only — auto-detect triggers
ios_trigger_files:
  - BMBFeatureData.swift
  - BMBFeatureStatusHelper.swift
  - BMBFeatureStatusHelper.m
```

**Tell the user** which defaults are active at the start of switch analysis:
```
Using default BMB Gateway data sources:
  Feature switches: Confluence page 1703299218 (Function Data)
  Config properties: Confluence page 1399770386 (Gateway Config)
To override: create .arbiter/switch-analysis.yml
```

---

> **iOS projects:** Steps 1–3 and the entry-point check in Step 6 use the patterns in
> §iOS-Specific Patterns below (one-hop `BMBFeatureData` constants). Steps 4, 5, 7 and 8 apply
> unchanged — iOS reads the same Function Data and Gateway Config sources. A user-supplied export
> (`--switch-data <dir>` with `function_data_confluence.json` and `gateway_config.txt`) replaces the
> Confluence fetch.

---

## Step 1 — Extract Switch References

Scan target class for all feature-gate patterns:
```bash
grep -n "session\.getAttribute\|isFeatureSwitchOn\|getBooleanProperty\|getStringProperty" TargetClass.java
grep -n "getThrottleMode\|GATEWAY_MODE\|VIA_API_MODE\|PARALLEL_MODE" TargetClass.java
```

For each match, extract the constant name passed as argument.

---

## Step 2 — Auto-Discover Constants Classes

Do NOT assume file paths. Discover them from the codebase:

```bash
# Find session-key constants class (holds keys used in session.getAttribute)
find src/main/java -name "*.java" | xargs grep -l "session attribute\|HttpSession\|SESSION" 2>/dev/null | \
  xargs grep -l "public static final String" | head -5

# Find config-key constants class (holds keys used in configValues.get*)
find src/main/java -name "*.java" | xargs grep -l "getBooleanProperty\|getStringProperty\|getIntegerProperty" 2>/dev/null | \
  grep -i "constant\|config\|key" | head -5

# Resolve a constant value once the file is located
grep -n 'CONSTANT_NAME\s*=' <discovered-file>.java
```

**Few-shot examples — what this looks like in different projects:**

```
BMB Gateway:
  session keys → src/main/java/.../gateway/operation/OperationConstants.java
  config keys  → src/main/java/.../gateway/service/ConfigurationKeyConstants.java

Another Spring Boot project:
  session keys → src/main/java/.../web/SessionAttributeKeys.java
  config keys  → src/main/java/.../config/AppConfigKeys.java

Properties-file project (no constants class):
  grep -rn "getBooleanProperty\|@Value\(\"" src/main/java/ | grep "switch\|feature\|enabled"
```

---

## Step 3 — Two-Hop Constant Resolution

Many codebases separate session-attribute keys from config-property keys. Trace the chain:

```
code reads:  session.getAttribute(SessionKeys.FEATURE_X)
               ↓ resolve SessionKeys.FEATURE_X → "feature_x_enabled"
               ↓ grep codebase for session.setAttribute("feature_x_enabled", ...)
               ↓ that setter reads: configValues.getBooleanProperty(ConfigKeys.FEATURE_X)
               ↓ resolve ConfigKeys.FEATURE_X → "myapp.feature.x.enabled"
               ↓ look up "myapp.feature.x.enabled" in config_properties source → get value
```

If no two-hop (config read directly in the same place as feature gate) — single lookup suffices.

---

## Step 4 — Look Up Switch State

**Feature switches lookup (JSON format):**
```python
import json, re
from collections import Counter

with open(cache_file) as f:
    data = json.load(f)

entry = data.get("SWITCH_NAME", {})

# Per-environment resolution — check named prod envs BEFORE ALL
# ALL is a catch-all/default; named envs (GLLIVE, SLLIVE, etc.) override it
PROD_ENVS = ["GLLIVE", "SLLIVE", "SLAWSLIVE", "GLAWSLIVE"]
per_env_statuses = {env: (entry.get(env) or {}).get("status") for env in PROD_ENVS if env in entry}
all_status = (entry.get("ALL") or {}).get("status")

# Effective status: if ANY named prod env is ON → ON; if ALL named prod envs are OFF → OFF
# If no named envs present, fall back to ALL.status
if per_env_statuses:
    prod_values = [s for s in per_env_statuses.values() if s is not None]
    if any(s == "ON" for s in prod_values):
        status = "ON"    # at least one prod env has the feature live
    elif all(s == "OFF" for s in prod_values):
        status = "OFF"   # all prod envs explicitly OFF
    else:
        status = all_status  # mixed nulls — fall back to ALL
else:
    status = all_status  # no per-env data, use ALL

# Auto-detect version prefix and sentinel from data (with safety checks)
all_versions = [
    v["version"] for e in data.values() if isinstance(e, dict)
    for v in (e.get("ALL") or {}).get("appVersions", [])
    if v.get("version")
]

# Detect prefix: most common non-numeric leading chars (SAFE: handle empty case)
if all_versions:
    # Extract all matching prefixes
    prefixes = [m.group() for v in all_versions 
                for m in [re.match(r'^[A-Z_]+', v)] if m]
    # Use most common prefix if any found (defensive: guard on prefixes, then on most_common result)
    most_common_result = Counter(prefixes).most_common(1) if prefixes else []
    prefix = most_common_result[0][0] if most_common_result else ""
else:
    prefix = ""  # No version data; use empty prefix

# Detect sentinel: version that appears with value 9999 or similar max
# Only set sentinel if we have both prefix AND versions to work with
# If prefix is empty or no versions available, use None (explicit, not a false value)
# Note: Empty prefix means we don't know the sentinel format, so filtering cannot be applied safely
if prefix and all_versions:
    sentinel = next((v for v in all_versions if re.sub(prefix, '', v) == '9999'), f"{prefix}9999")
else:
    sentinel = None  # No valid prefix or versions; cannot determine sentinel safely

# Calculate latest version number
# NOTE: When sentinel = None, we only reach this block if prefix and all_versions are truthy
# (from the outer if), so sentinel will never actually be None here. The check
# (sentinel is None or v != sentinel) is defensive; v != sentinel is what applies.
numeric = []
if prefix and all_versions:
    numeric = [int(v.replace(prefix, '')) for v in all_versions
               if (sentinel is None or v != sentinel) and v.startswith(prefix) and v.replace(prefix,'').isdigit()]
latest = max(numeric) if numeric else None

# Calculate entry version age
# NOTE: Same as above - sentinel will not be None inside this block, but the check
# is defensive to handle any future code changes. When sentinel is not None,
# we filter out v["version"] == sentinel to exclude the sentinel version from age calculation.
entry_versions = (entry.get("ALL") or {}).get("appVersions", [])
entry_numeric = []
if prefix and entry_versions:
    entry_numeric = [int(v["version"].replace(prefix,'')) for v in entry_versions
                     if v.get("version","").startswith(prefix) and (sentinel is None or v["version"] != sentinel)
                     and v["version"].replace(prefix,'').isdigit()]
min_ver = min(entry_numeric) if entry_numeric else None
# NOTE: Use 'is not None' to handle zero versions correctly (e.g., BMB_00000)
# Using 'if latest and min_ver' would treat 0 as falsy, skipping valid versions
age = (latest - min_ver) if latest is not None and min_ver is not None else None
```

**Config properties lookup (pipe-delimited table):**
```bash
# key_column=2, value_column=7 (1-based) — adjust per config
grep -i "myapp.feature.x.enabled" .arbiter/cache/gateway_config.txt | \
  awk -F'|' '{gsub(/ /,"",$7); print $7}'
```

**Git history lookup (EXPERIMENTAL — supporting evidence only):**
```bash
git log --oneline --all -S "SWITCH_NAME" -- src/main/java/ | head -5
git show --no-patch --format="%ai %s" <oldest_commit_hash>
```
Git signals are supporting evidence only — never use git alone to auto-classify dead.
Always escalate to user prompt when switch is absent from both configured data sources.

---

## Step 5 — Classify & Boost

Apply classification matrix from `references/classification-matrix.md`.

**Critical rule — OFF ≠ dead:** `OFF` means the new feature is not yet deployed.
The if-block is upcoming code. Only classify as dead if user explicitly confirms abandoned.

Apply confidence boost (only values +0.5, +1.0, +1.5 permitted — see matrix).
**If classification verdict is KEEP ALL → skip the boost formula entirely. Boost = 0, no flag.**

---

## Step 6 — Cascade & Exception

**Cascade rule:** Check ALL callers of each class inside the dead block — across the entire codebase:
```bash
grep -rn "ClassName\|methodName" src/main/java/ --include="*.java" | grep -v "DeadGateFile.java"
# Zero external callers → exclusively called from dead block → cascade dead
# Any external callers → cascade = LIKELY not SAFE — note them in report
```

Cascade always LIKELY (not SAFE) when callee is in a shared helper class. A shared helper is any class NOT acting as an operation dispatcher (no `@Component("OPCODE")` or equivalent entry-point annotation) that lives in a `helper`, `util`, `facade`, `service`, or `impl` package.

**Entry point exception:** Detect operation dispatchers with:
```bash
# Spring @Component with opcode string
grep -n '@Component\s*(\s*"[A-Z][A-Z0-9]*"' TargetClass.java
# Spring XML bean registration
grep -n 'id="[A-Z][A-Z0-9]*"' src/main/resources/**/*.xml
```
If match found → class is an operation dispatcher → **never delete the class**, only the body inside the dead `if` block.

---

## Step 7 — User Prompt (Hard Stop for Unresolved Switches)

**STOP here if any switch reaches "ASK USER" verdict.**
- Do NOT assign any score to unresolved switches
- Do NOT continue to Step 8 output
- Collect ALL unresolved switches into a single message
- Wait for user response before proceeding

```
Switch not fully resolved: SWITCH_NAME

Evidence → ABANDONED (if-block = dead):
  • Not in feature_switches data source
  • Not in config_properties data source
  • Last commit: [date] ([message])

Evidence → UPCOMING (keep everything):
  • [any conflicting signals]

Choose:
  A) Abandoned — delete if-block (SAFE 3.5)
  B) Upcoming — keep everything
  C) Wrong key — correct name: ___
```

---

## Step 8 — Output

Append `SWITCH ANALYSIS AUGMENTATION` section to standard arbiter report.
**Do NOT hardcode page IDs — read from active config (YAML or defaults).**
```
SWITCH ANALYSIS AUGMENTATION
==============================
Sources: <feature_switches.name> (page <feature_switches.confluence_page_id>, Xd old)
       | <config_properties.name> (page <config_properties.confluence_page_id>, Xd old)
[If overridden: Sources loaded from .arbiter/switch-analysis.yml]

Resolutions:
  SWITCH_NAME  OFF → KEEP ALL (upcoming feature)
  SWITCH_NAME  ON age=791 → else-block DEAD (+0.5 boost)
  prop.key     config=true → else-block DEAD (+1.5 boost)
  SWITCH_NAME  NOT FOUND both sources → awaiting user input

Promoted candidates:
  Entity           File:Line    Before → After    Reason

User input required:
  [switch name] — [reason for conflict]
```

Cache results to `.arbiter/cache/switch_analysis.json`.

---

## iOS-Specific Patterns

**iOS patterns owner:** Pratik Goswami

### Trigger Detection

iOS switch analysis only activates when the scanned module contains iOS feature-gate files:

```bash
find . -name "BMBFeatureData.swift" -o -name "BMBFeatureStatusHelper.swift" -o -name "BMBFeatureStatusHelper.m" | head -1
# If found → activate iOS switch analysis
```

### Feature Gate Patterns to Scan

**BMBFeatureStatusHelper** (primary feature switch API):
```swift
// Pattern 1: Modern Bool API
BMBFeatureStatusHelper.sharedInstance().isOn(BMBFeatureData.PropertyName)
BMBFeatureStatusHelper.isOn(BMBFeatureData.PropertyName)

// Pattern 2: Status enum API
BMBFeatureStatusHelper.sharedInstance().statusForFeature(BMBFeatureData.PropertyName) == .ON
BMBFeatureStatusHelper.sharedInstance().status(forFeature: BMBFeatureData.PropertyName)

// Pattern 3: ObjC interop
[BMBFeatureStatusHelper.sharedInstance statusForFeature:BMBFeatureData.PropertyName]
```

**Regex patterns:**
```
BMBFeatureStatusHelper[.\w]*(?:isOn|statusForFeature|status\(forFeature)\s*[\(:]?\s*(?:BMBFeatureData\.)?(\w+)
```

**BMBPolicyValueHelper** (policy values):
```swift
// Pattern 1: Boolean policy
BMBPolicyValueHelper.isFeaturePolicyEnabled(for: BarclaysPolicyType.PolicyName)

// Pattern 2: String policy
BMBPolicyValueHelper.policyValue(for: BarclaysPolicyType.PolicyName)
```

**PlatformSession** (newer approach):
```swift
PlatformSession.sharedInstance.settings?.status(for: .appFunctionKey)
PlatformSession.sharedInstance.settings?.value(for: .policyKey)
```

### Constant Resolution (One-Hop)

iOS constants map directly from Swift property to string key:

```
BMBFeatureData.ConfirmationOfPayee → "COP"
BMBFeatureData.transferAndOffersAPIMigration → "BCard_BT_MT_Migration"
BMBFeatureData.SSPScheduledPayments → "SSP_SCHEDULED_PAYMENTS"
```

**Resolution steps:**
1. Auto-discover all `BMBFeatureData` files: `grep -rn "extension BMBFeatureData" --include="*.swift"`
2. Parse `static let PropertyName = "STRING_KEY"` declarations
3. Build lookup: `{PropertyName → STRING_KEY}`
4. For each gate reference, resolve property name to string key
5. Look up string key in Function Data (feature_switches source)

**Policy constants** follow the same pattern via `BarclaysPolicyType`:
```
BarclaysPolicyType.ManagePaymentsPolicy → "ManagePaymentsDepositaCheque"
```

### iOS Entry Point Exception

These classes are **never fully deleted** even if their master switch is OFF:

- Classes annotated with `@main` or `@UIApplicationMain`
- `UIApplicationDelegate` conformers
- Root view controllers referenced in `Main.storyboard` or `Info.plist` (`UIMainStoryboardFile`)
- Coordinator classes that dispatch to multiple feature flows

**Rule:** Delete only the dead if-block body inside the gated method. Keep the else block (it runs today).

---

## Additional Resources

- **`references/classification-matrix.md`** — Full classification matrix, boost formula, critical rules
- **`references/bmb-gateway-examples.md`** — Concrete examples from bmb-gateway (COP01, WLB, COMPLEX_MANDATE)
- **`references/bmb-ios-examples.md`** — Concrete examples from the BMB iOS app
