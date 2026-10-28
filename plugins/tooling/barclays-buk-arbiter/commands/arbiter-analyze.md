---
name: arbiter-analyze
agent: arbiter-analyze-agent
allowed-tools: [Bash, Read, Glob, Grep, Write]
description: "Build call graph and identify dead code candidates with confidence scoring"
---

# Analyze: Call Graph & Dead Code Identification

Build comprehensive call graph to identify dead code candidates and assign confidence scores.

## Arguments

```
[PATH]           Repository path (default: current directory)
LANGUAGE         Language override (java, python, javascript, etc.)
--scope all      Analyze all files (default)
--scope file     Analyze single file or pattern
--min-confidence 0-4  Minimum confidence threshold (default: 1)
--technology TECH   Target technology: java | ios (default: auto-detect)
--module MODULE     Target a specific submodule/package (optional)
```

## Technology Routing

| Technology | Agent |
|---|---|
| `java` | arbiter-analyze-agent |
| `ios` | arbiter-discover-analyze-ios-agent |

If `--technology` is not provided, the technology is auto-detected (`*.xcodeproj`, `*.xcworkspace`, `Package.swift` → ios; `pom.xml`, `build.gradle` → java).

## Example

```
/arbiter-analyze .
/arbiter-analyze /path/to/repo --language java
/arbiter-analyze . --scope "src/main/**/*.java" --min-confidence 2

# iOS
/arbiter-analyze . --technology ios
/arbiter-analyze . --technology ios --module NetworkKit
```

## Output

Analysis report with:
- Call graph (method A calls B, etc.)
- Dead code candidates by category (SAFE, LIKELY, UNCERTAIN, KEEP)
- Confidence scores for each candidate

### iOS-specific output
- Resource references (Storyboard, XIB, plist)
- Dynamic dispatch patterns detected
- Framework-managed entities identified
- Objective-C candidates are listed for review only (not removed)

## Next Step

Once analysis completes, run `/arbiter-plan` to convert findings into executable removal tasks.
