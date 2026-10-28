# Compiled JAR Fallback Extraction

When EBS/EGS **source JARs** (`-sources.jar`) are not available in the Gradle cache, use compiled JARs as a fallback. This file defines the 3-tier hybrid extraction approach. Both the discovery agent (Steps 1.10-1.13) and single-service mode (Steps S.7a-S.7e) reference this file.

**Priority order:**
1. **MIS source repo** (`~/.mts-source/`) — if `MIS_REPO_PATH` is set and Transaction class found (see `mis_source_extraction.md`)
2. **Source JAR** (`-sources.jar`) — if available in Gradle cache
3. **Compiled JAR fallback** (Tier 1 → Tier 2 → Tier 3) — only when neither MIS source nor source JAR is available

---

## 3-Tier Extraction Approach

### Tier 1: Constant Pool Parser

Reads `.class` bytes directly from a compiled JAR via `zipfile` + `struct`. Extracts class name, superclass, all string constants (including WMID parameters and WMOD fields), method references, and field references. Operates using Python stdlib only — no external dependencies. Provides exact class hierarchy, exact WMID/WMOD string lists, and DataGroup/Gateway refs. Program and version codes are heuristic at this tier.

See `compiled-jar-constant-pool.md` for Tier 1 code.

### Tier 2: ROP/RIP File Parser

EGS compiled JARs contain structured diagnostic report files at `riprop/*.ROP` and `riprop/*.RIP`. ROP (Response Output Parse) files define WMOD response fields; RIP (Request Input Parse) files define WMID request parameters. Both include data types and field lengths. This tier provides definitive, authoritative lists for WMID parameters and WMOD response fields.

See `compiled-jar-rop-rip.md` for Tier 2 code.

### Tier 3: javap Bytecode Disassembly

Uses the JDK `javap` tool to extract exact values from compiled bytecode. Only activates when `javap` is available on the system. Provides exact `getProgramCode()` / `getVersionCode()` return values and definitive DataGroup-to-WMID conditional mappings by parsing constructor bytecode patterns. This is the only tier that can determine which DataGroup condition gates each WMID parameter.

See `compiled-jar-javap.md` for Tier 3 code.

---

## Confidence Assignment Rules

Each extracted data item receives a confidence tag based on the extraction tier used.

| Level | Tag | Condition |
|-------|-----|-----------|
| Highest | `verified-from-source` | Extracted from `-sources.jar` (existing approach, unchanged) |
| Highest | `verified-from-mis-source` | Extracted directly from MIS GitLab source repo at `~/.mts-source/` (see `mis_source_extraction.md`) |
| High | `verified-from-bytecode` | Extracted from compiled JAR — constant pool (Tier 1) + javap confirmation (Tier 3) |
| High | `verified-from-rop-rip` | Cross-validated against ROP/RIP files (Tier 2) |
| Medium | `partial-from-bytecode` | Constant pool extraction only (Tier 1), no javap available |
| Low | `inferred-from-convention` | Derived from naming patterns (existing approach, unchanged) |

### Assignment Logic

```
For each data item:
  IF source JAR was available:
    confidence = "verified-from-source"
  ELIF compiled JAR was used:
    IF item also appears in ROP/RIP:
      confidence = "verified-from-rop-rip"
    ELIF javap was available AND confirmed the value:
      confidence = "verified-from-bytecode"
    ELSE:
      confidence = "partial-from-bytecode"
  ELSE:
    confidence = "inferred-from-convention"
```

### Per-Item Confidence Rules

1. **Transaction class identity** (program code, version code, composed name):
   - From source JAR: `verified-from-source`
   - From compiled JAR constant pool + javap `ldc`+`areturn`: `verified-from-bytecode`
   - From constant pool short-string heuristic only: `partial-from-bytecode`
   - From naming convention: `inferred-from-convention`

2. **DataGroup-to-WMID mappings:**
   - From source JAR: `verified-from-source`
   - From RIP files (Tier 2): `verified-from-rop-rip`
   - From constant pool WMID strings + javap conditional patterns: `verified-from-bytecode`
   - From constant pool WMID strings only (list complete, conditional mapping lost): `partial-from-bytecode`
   - From convention: `inferred-from-convention`

3. **WMOD response fields:**
   - From source JAR: `verified-from-source`
   - From ROP files (Tier 2): `verified-from-rop-rip` (includes data types and lengths)
   - From constant pool WMOD strings: `verified-from-bytecode`
   - From convention: `inferred-from-convention`

4. **Command class gateway calls:**
   - From source JAR: `verified-from-source`
   - From compiled JAR method refs + field refs (Tier 1): `verified-from-bytecode`
   - From convention: `inferred-from-convention`

### Downstream Impact

- `verified-from-source` and `verified-from-bytecode`: No warnings in generated docs
- `verified-from-rop-rip`: No warnings — ROP/RIP files are authoritative
- `partial-from-bytecode`: Mark with note: "Extracted from compiled JAR (constant pool). DataGroup-to-WMID conditional attribution not available without javap."
- `inferred-from-convention`: Existing "Needs verification" markers remain unchanged

### Graceful Degradation

- **javap available:** Full Tier 1 + 2 + 3 — exact values for everything. Confidence = `verified-from-bytecode` or `verified-from-rop-rip`.
- **javap NOT available:** Tier 1 + 2 only — ~85% coverage. Gap: DataGroup-to-WMID conditional attribution (which DataGroups trigger which WMIDs). WMID list is still complete, but cannot determine which DataGroup condition gates each one. Confidence = `partial-from-bytecode`.
- **No compiled JAR either:** Falls back to `inferred-from-convention` (existing behaviour).
