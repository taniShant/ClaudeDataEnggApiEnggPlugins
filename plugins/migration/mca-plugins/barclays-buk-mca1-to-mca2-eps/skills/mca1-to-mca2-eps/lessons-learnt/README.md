# Lessons Learnt — MCA1 to MCA2 Migration

This directory stores lessons learnt from real migration runs. Each migration generates a project-specific file that captures decisions, pitfalls encountered, and resolutions.

## How It Works

1. **During migration:** The agent logs key decisions and issues to `{PROJECT_PATH}/mca1-to-mca2-lessons.md`
2. **After migration:** Recurring patterns are aggregated into `PATTERNS.md`
3. **Before future migrations:** The agent reads `PATTERNS.md` to avoid known pitfalls

## Files

| File | Purpose |
|------|---------|
| `PATTERNS.md` | Aggregated recurring issues and resolutions |
| `example-project.md` | Template for per-project lesson files |
