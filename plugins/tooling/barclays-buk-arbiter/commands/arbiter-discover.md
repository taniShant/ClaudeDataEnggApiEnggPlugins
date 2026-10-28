---
name: arbiter-discover
agent: arbiter-discover-agent
allowed-tools: [Bash, Read, Glob, Grep]
description: "Detect programming languages and frameworks in repository"
---

# Discover: Language & Framework Detection

Scan the repository to detect languages, build systems, and frameworks. Routes to `arbiter-discover-agent`.

## Arguments

```
[PATH]          Repository path (default: current directory)
--quick         Incremental scan (changed files only)
--languages     Comma-separated list (default: java)
--exclude       Exclude patterns (default: target/,build/,.git/)
--technology TECH   Target technology: java | ios (default: auto-detect)
--module MODULE     Target a specific submodule/package (optional)
--scheme SCHEME     Xcode scheme for build system detection (iOS only)
```

## Technology Routing

| Technology | Agent |
|---|---|
| `java` | arbiter-discover-agent |
| `ios` | arbiter-discover-analyze-ios-agent |

If `--technology` is not provided, the technology is auto-detected (`*.xcodeproj`, `*.xcworkspace`, `Package.swift` → ios; `pom.xml`, `build.gradle` → java).

iOS defaults: `--languages swift,objc`, `--exclude Pods/,Carthage/,DerivedData/`. On iOS, discovery and analysis run as one phase.

## Example

```
/arbiter-discover .
/arbiter-discover /path/to/repo --languages java,kotlin
/arbiter-discover . --quick  # Incremental scan

# iOS
/arbiter-discover . --technology ios
/arbiter-discover . --technology ios --module PaymentKit --scheme MyApp
```

## Output

Language detection report in JSON format, recommending analyzer tier and estimated time.

### iOS
Entity inventory, resource/dispatch scans and scored candidates in `.arbiter/swift/` (ENTITIES.json, RESOURCE_REFS.json, DISPATCH_SCAN.json, CONFIDENCE.json).

## Next Step

Once discovery completes, run `/arbiter-analyze` to build call graph and identify dead code candidates.
