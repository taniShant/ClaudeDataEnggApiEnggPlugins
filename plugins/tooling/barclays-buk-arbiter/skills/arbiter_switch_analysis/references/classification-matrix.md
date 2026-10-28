# Switch Classification Matrix & Confidence Boost Formula

## Status Resolution — Per-Environment Precedence

**Before applying the matrix, resolve the effective status:**

Named production environments (`GLLIVE`, `SLLIVE`, `SLAWSLIVE`, `GLAWSLIVE`) override `ALL`:
- ANY named env = `ON` → effective status = **ON** (feature live in at least one prod env)
- ALL named envs = `OFF` → effective status = **OFF** (feature off in all prod envs)
- No named envs present → use `ALL.status` as fallback

**Why this matters:** `ALL.status=OFF` with `GLLIVE=ON` means the feature IS live in production. Treating it as OFF would produce false dead-code verdicts. Always check per-env fields first.

## Classification Matrix

Apply in order. First matching row wins. Use **effective status** (resolved above), not raw `ALL.status`.

| Function Data | Config page | Git age | Code pattern | Dead code verdict |
|---|---|---|---|---|
| `status=OFF` | entry exists (`false`) | any | any | **KEEP ALL** — in DB + OFF = upcoming |
| `status=OFF` | no entry | any | if-block calls XAPI/new | **KEEP ALL** — upcoming feature |
| `status=OFF` | no entry | >12 months | if-block calls legacy/IMS | **ASK USER** — possibly abandoned |
| `NOT FOUND` | entry exists (`false`) | any | any | **KEEP ALL** — planned, confirmed in DB |
| `NOT FOUND` | entry exists (`true`) | any | any | **if-block LIVE, else-block DEAD** |
| `NOT FOUND` | no entry | <6 months | any | **KEEP ALL** — too new to judge |
| `NOT FOUND` | no entry | 6–12 months | signals conflict | **ASK USER** |
| `NOT FOUND` | no entry | >12 months | commit says "renamed"/"replaced" | **if-block DEAD** (SAFE 3.5) |
| `NOT FOUND` | no entry | >12 months | if-block calls legacy/IMS | **if-block DEAD** (SAFE 3.5) |
| `NOT FOUND` | no entry | >12 months | signals conflict | **ASK USER** |
| `status=ON` | any | age ≥ 1000 | else-block calls legacy/IMS | **else-block DEAD** (higher confidence) |
| `status=ON` | `true` | age ≥ 500 | else-block calls legacy/IMS | **else-block DEAD** |
| `status=ON` | any | age < 500 | any | **KEEP ALL** — too recent |

## Code Pattern Signals

### NEW path in if-block (feature being introduced — KEEP):
- Calls methods containing `Api`, `Xapi`, `New`, `Migration`, `V2`
- Calls REST/HTTP clients
- Variable named `isXxxMigrationEnabled`, `isXxxNewEnabled`, `isXxxApiEnabled`
- Comment references new ticket/PWR number

**iOS (Swift):**
- Calls methods containing `New`, `Migration`, `V2`, `Updated`, `Modern`
- Uses newer APIs (URLSession, Combine, async/await vs legacy completion handlers)
- Variable named `isXxxMigrationEnabled`, `isXxxNewFlowEnabled`
- Comment references JIRA ticket for new feature

### OLD path in else-block (legacy dead code — DELETE):
- Calls `ServiceRequestor.execute()` (IMS/mainframe)
- Calls methods containing `Legacy`, `Old`, `V1`, `Bps`, `Mts`, `Mainframe`
- Comment says "legacy", "old path", "fallback", "before migration"

**iOS (Swift):**
- Calls methods containing `Legacy`, `Old`, `V1`, `Deprecated`, `Previous`
- Uses deprecated APIs (NSURLConnection, UIWebView, older ObjC patterns)
- Comment says "legacy", "old flow", "fallback", "before migration"
- Uses ObjC bridging patterns where Swift equivalent exists

## Confidence Boost Formula

Apply **on top of** base arbiter score. Never replaces it.

**Only three valid boost values: +0.5, +1.0, +1.5. No other values permitted.**
If no row below matches exactly → boost = 0, flag candidate for manual review.

```
TRIGGER                                          BOOST   TARGET BLOCK
────────────────────────────────────────────────────────────────────
Config page explicit value = true                +1.5    else-block dead
User confirms switch abandoned (NOT FOUND path)  +1.5    if-block dead
Function Data ON + age ≥ 1500                    +1.5    else-block dead
Function Data ON + 1000 ≤ age < 1500             +1.0    else-block dead
Function Data ON + 500 ≤ age < 1000              +0.5    else-block dead
────────────────────────────────────────────────────────────────────
Any other situation                              +0.0    no boost, flag
```

final_score = clamp(base_score + switch_boost, 0, 4)

## Critical Rules

### OFF switch ≠ dead code
`OFF` means the new feature is not yet deployed. The if-block is **upcoming code — KEEP**.
Only `OFF` + user confirms abandoned → if-block dead.

### Config page `false` ≠ dead code
`false` means feature disabled but **exists in DB = planned**. KEEP everything.
Only explicit `true` → else-block dead.

### No DB entry ≠ dead code (REMOVED RULE)
Absence from DB means the code runs on the property default. The default could be `true` or `false` — absence alone is not conclusive.

**Critical distinction between absence and explicit values:**

**No DB entry (absent):** Do NOT boost. Inconclusive.
- Property not found in config_properties source
- Code runs on application default (unknown to arbiter)
- Cannot determine if default is true or false
- Result: No boost. Flag for manual review if needed.

**Explicit DB entry with `value = true`:** DO boost (+1.5). Confirmed value, not absence.
- Config page shows explicit value = true
- This is a confirmed DB entry, not an absence
- Indicates the if-block is active and the else-block is dead
- Result: Apply +1.5 boost per formula (line 57)

**Why this distinction matters:**
- Absence (no data) → Cannot conclude → No boost
- Explicit presence with true value (confirmed data) → Can conclude → Boost applies

Only boost from explicit confirmed values in the DB. Never boost based on absence alone.

### Throttle mode (NOT YET SUPPORTED)
`PT_GATEWAY_MODE` / `PT_VIA_API_MODE` / `PT_PARALLEL_MODE` routing is not yet resolved by this skill. Flag throttle-gated blocks as UNCERTAIN pending manual review.

### Operation entry point exception
`@Component("OPCODE")` classes (e.g. `@Component("COP01")`) are **never fully deleted** even if master switch is OFF.
- The opcode routing still requires the class
- Delete only the `if (featureEnabled)` block body inside execute()
- Keep the `else` block — it runs today (returns feature-disabled error)

### iOS entry point exception
`@main` / `@UIApplicationMain` classes, `UIApplicationDelegate` conformers, and root view controllers referenced in storyboards are **never fully deleted**. Delete only the dead if-block body. Keep the else block.

## Pattern Examples (generic)

### Feature switch OFF — upcoming feature, KEEP ALL
```java
if (isNewFeatureEnabled) {     // switch=OFF → never runs
    callNewApiPath();            // UPCOMING — KEEP
} else {
    callLegacyPath();            // LIVE today — KEEP
}
```
OFF = feature not deployed. Both branches KEEP. Most common mistake: treating OFF as dead.

### Config property true — else-block dead
```java
if (isFeatureEnabled) {         // config=true → always true
    callEnabledPath();           // KEEP — always runs
} else {
    callDisabledPath();          // DEAD → delete (+1.5 boost)
}
```
Boost: +1.5 from explicit DB value. Cascade: grep `callDisabledPath` across all files.

### Feature switch ON + stale — else-block dead
```java
if (isFeatureEnabled) {         // ON since version X, age > threshold → always true
    callNewPath();               // KEEP — current live path
} else {
    callOldLegacyPath();         // DEAD → delete (boost by age tier)
}
```
Boost: +0.5 / +1.0 / +1.5 depending on age tier (see matrix).

### NOT FOUND in both sources — human decision required
- Switch not in feature_switches source
- Property not in config_properties source
- Git age > 12 months with no recent commits
- **STOP — ask user before scoring**
- User confirms abandoned → if-block DEAD (SAFE 3.5, +1.5 boost)
- User confirms upcoming → KEEP ALL

For concrete bmb-gateway examples (COP01, WLB, COMPLEX_MANDATE_CHEQUE_IMAGING):
see `references/bmb-gateway-examples.md`

For iOS examples: see `references/bmb-ios-examples.md`
