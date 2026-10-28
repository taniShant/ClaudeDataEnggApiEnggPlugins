# Repository Deduplication Reference

This document defines the rules and examples for deduplicating Gradle repository declarations during Phase 0 of the MCA JDK upgrade migration.

## Deduplication Rules (CRITICAL — READ CAREFULLY)

### Priority Order

1. **Identify ALL unique repositories that have credentials** (username/password)
   - "Unique" means different URLs, not just different formatting
   - If two repos have same URL, keep only one (with credentials if present)
2. **Keep ALL unique repositories WITH credentials** (typically releases + snapshots repos)
   - `barclays-restricted-releases` with credentials → KEEP
   - `barclays-restricted-snapshots` with credentials → KEEP
   - NEVER merge or remove these — they are needed for different artifact types
3. **Keep ALL unique Barclays Nexus repositories WITHOUT credentials**
   - `buk-maven2-group` → KEEP (group repository with specific artifacts)
   - `buk-releases` → KEEP (individual repository)
   - `barclays/` → KEEP (general group repository)
   - `barcorpnexus` → KEEP (corporate nexus)
   - These are DIFFERENT repos serving DIFFERENT artifacts — do NOT assume "one is enough"
4. **Remove ONLY true duplicates** (same exact URL appearing multiple times)
   - `https://nexus.barcapint.com/.../barclays/` appearing twice → remove one copy
   - `buk-maven2-group` vs `barclays/` → NOT duplicates (keep both)
5. **NEVER keep** `mavenCentral()`, `gradlePluginPortal()`, or other non-Barclays public repos
6. **If NO repositories have credentials at all**, keep ALL unique Barclays Nexus repositories

### Anti-Pattern (NEVER DO THIS)

Strategy: "Keep 2 credential repos + 1 general barclays/ repo" — **WRONG**. This collapses ALL non-credential repos into one. `buk-maven2-group`, `buk-releases`, `barcorpnexus` are NOT interchangeable with `barclays/`. Keep ALL unique URLs.

**Correct strategy**: Keep ALL credential repos + ALL unique non-credential repos, removing only entries whose EXACT URL appears more than once.

### Cross-Block Merge Rules

Gradle files may have MULTIPLE repository blocks:
1. `buildscript.repositories` (for build-time dependencies)
2. `repositories` (for compile-time dependencies)
3. `allprojects.repositories` (in multi-module projects)
4. `subprojects.repositories` (in multi-module projects)

**Merge procedure:**

1. **Collect** ALL repositories from ALL blocks
2. **Create a UNION set** of all unique repos from all blocks
3. **Apply** the same deduplicated list to EVERY block

If a repo exists in ANY block, it must exist in ALL blocks after merge. Example: `barcorpnexus` was only in `repositories` → must be added to `buildscript` too.

### `mavenContent` Filters

Use `mavenContent` blocks to distinguish release vs snapshot repos:
- Repos with URL containing `releases` → add `mavenContent { releasesOnly() }`
- Repos with URL containing `snapshots` → add `mavenContent { snapshotsOnly() }`

---

## Scenario 1: Multiple repository blocks with different credentials

**CRITICAL CASE**: When `buildscript.repositories` has one credential repo and `repositories` has a different credential repo, you MUST preserve BOTH in the merged result.

**Before:**
```gradle
buildscript {
    repositories {
        maven { url "https://nexus.barcapint.com/nexus/content/groups/barclays/" }
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases'
            credentials {
                username 'user'
                password 'pass'
            }
        }
    }
}

repositories {
    maven { url "https://nexus.barcapint.com/nexus/content/groups/barclays/" }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-snapshots'
        credentials {
            username 'user'
            password 'pass'
        }
    }
}
```

**After (BOTH credential repos preserved in BOTH blocks):**
```gradle
buildscript {
    repositories {
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases'
            credentials {
                username 'user'
                password 'pass'
            }
            mavenContent {
                releasesOnly()
            }
        }
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-snapshots'
            credentials {
                username 'user'
                password 'pass'
            }
            mavenContent {
                snapshotsOnly()
            }
        }
        maven {
            url 'https://nexus.barcapint.com/nexus/content/groups/barclays/'
        }
    }
}

repositories {
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases'
        credentials {
            username 'user'
            password 'pass'
        }
        mavenContent {
            releasesOnly()
        }
    }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-snapshots'
        credentials {
            username 'user'
            password 'pass'
        }
        mavenContent {
            snapshotsOnly()
        }
    }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/barclays/'
    }
}
```

---

## Scenario 2: Multiple repositories with credentials in same block

**Before:**
```gradle
buildscript {
    repositories {
        maven { url "https://nexus.barcapint.com/nexus/content/repositories/buk-releases" }
        maven { url "https://nexus.barcapint.com/nexus/content/groups/buk-maven2-group/" }
        maven { url "https://nexus.barcapint.com/nexus/content/groups/barclays/" }
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases'
            credentials {
                username 'user'
                password 'pass'
            }
        }
        maven { url "https://nexus.barcapint.com/nexus/content/repositories/buk-releases" }  // duplicate URL!
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-snapshots'
            credentials {
                username 'user'
                password 'pass'
            }
        }
    }
}
repositories {
    maven { url 'https://nexus.barcapint.com/nexus/content/repositories/buk-releases' }
    maven { url = 'https://nexus.barcapint.com/nexus/content/groups/buk-maven2-group' }
    maven { url = 'https://nexus.barcapint.com/nexus/content/groups/barclays/' }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases'
        credentials {
            username 'user'
            password 'pass'
        }
    }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-snapshots'
        credentials {
            username 'user'
            password 'pass'
        }
    }
}
```

**After:**
```gradle
buildscript {
    repositories {
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases'
            credentials {
                username 'user'
                password 'pass'
            }
            mavenContent {
                releasesOnly()
            }
        }
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-snapshots'
            credentials {
                username 'user'
                password 'pass'
            }
            mavenContent {
                snapshotsOnly()
            }
        }
        maven { url 'https://nexus.barcapint.com/nexus/content/repositories/buk-releases' }
        maven { url 'https://nexus.barcapint.com/nexus/content/groups/buk-maven2-group/' }
        maven { url 'https://nexus.barcapint.com/nexus/content/groups/barclays/' }
    }
}
repositories {
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases'
        credentials {
            username 'user'
            password 'pass'
        }
        mavenContent {
            releasesOnly()
        }
    }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-snapshots'
        credentials {
            username 'user'
            password 'pass'
        }
        mavenContent {
            snapshotsOnly()
        }
    }
    maven { url 'https://nexus.barcapint.com/nexus/content/repositories/buk-releases' }
    maven { url 'https://nexus.barcapint.com/nexus/content/groups/buk-maven2-group/' }
    maven { url 'https://nexus.barcapint.com/nexus/content/groups/barclays/' }
}
```

**What happened:**
- `barclays-restricted-releases` with credentials → KEPT
- `barclays-restricted-snapshots` with credentials → KEPT
- `buk-maven2-group` → KEPT (group repository, serves different artifacts)
- `content/groups/barclays/` → KEPT (general group repository)
- `buk-releases` (duplicate URL — appeared twice) → one copy REMOVED, one KEPT

---

## Scenario 3: Only one repository with credentials

**Before:**
```gradle
repositories {
    maven { url 'https://nexus-read.barcapint.com/nexus/' }
    maven { url 'https://nexus.barcapint.com/nexus/content/groups/barclays/' }
    maven {
        url 'https://nexus.barcapint.com/nexus/'
        credentials {
            username 'user'
            password 'pass'
        }
    }
    maven { url 'https://nexus-read.barcapint.com/nexus/' }  // duplicate!
}
```

**After:**
```gradle
repositories {
    maven {
        url 'https://nexus.barcapint.com/nexus/'
        credentials {
            username 'user'
            password 'pass'
        }
    }
    maven { url 'https://nexus-read.barcapint.com/nexus/' }
    maven { url 'https://nexus.barcapint.com/nexus/content/groups/barclays/' }
}
```

Note: `nexus-read.barcapint.com` and `nexus.barcapint.com` are DIFFERENT hosts → both kept.
The duplicate `nexus-read` entry (appeared twice) → one copy removed.

---

## Build Verification After Deduplication

After applying deduplication, verify that dependency resolution still works:

```bash
$GRADLE_CMD dependencies --configuration compileClasspath > /dev/null 2>&1
```

If this fails, repository deduplication broke dependency resolution. Restore original `build.gradle` and log the error. This is a fatal error — cannot proceed without working repository config.
