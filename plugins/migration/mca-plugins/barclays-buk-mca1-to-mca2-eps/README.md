# barclays-buk-mca1-to-mca2-eps

MCA1 to MCA2 migration toolkit for Barclays Java microservices. Fully replaces all MCA1 patterns (`scp-eps-java-common`) with MCA2 equivalents (`mca-java-common`) using aggressive strategy — no stubs, no compatibility shims.

## Usage

```
/migrate-mca1-to-mca2 [project_path] [--target=PATH] [--plan-only] [--phase=N]
```

## What it does

Executes a 14-phase migration:

| Phase | Action |
|---|---|
| 0 | DevOps Gradle plugin consolidation |
| 1 | Build system (dependency swap) |
| 2 | Application bootstrap |
| 3 | XML to Java configuration |
| 4 | Controllers |
| 5 | Services (with business logic preservation) |
| 6 | Context & headers (IOL) |
| 7 | REST clients (gated — RestClient/MisClient choice) |
| 8 | Exception handling |
| 9 | Helpers & utilities |
| 10 | Filter chain |
| 11 | Testing (gated — write now or defer) |
| 12 | OAS3 specification |
| 13 | Process.json journey definitions |
| 14 | Package rename & cleanup (gated) |

Outputs a `TECH-DEBT-REPORT.md` with full audit trail after migration.

## Standards

Loads `barclays-buk-standards:security`, `barclays-buk-standards:api-design`, and `barclays-buk-standards:testing`.

## Author

MCA Core Engineering (mcaplatform@barclays.com)
