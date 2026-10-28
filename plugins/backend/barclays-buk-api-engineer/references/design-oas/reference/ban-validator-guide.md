# BAN Validator — Reference for verify-oas

Referenced by SKILL.md (verify-oas) and verify-oas command.

Barclays API Network (BAN) validator endpoint:
`https://barclays-api-network-26915.pr2.apaas4.barclays.intranet`

---

## Run the Validator

Script is resolved by the verify-oas command at runtime via:
```bash
BAN_SCRIPT_PATH=$(find "$USERPROFILE/.claude/plugins/cache" -path "*barclays-buk-api-engineer*" -name "ban_validator.py" 2>/dev/null | sort -V | tail -1)
```

```bash
python "$BAN_SCRIPT_PATH" "<spec-dir>/openapi.yaml" --all-files --format json -o "<spec-dir>/validator-response.json"
```

---

## Auth

- **Windows domain users:** Kerberos auto — no action needed
- **Mac/Linux:** set `BAN_USERNAME` + `BAN_PASSWORD` env vars

**Detecting auth failure:**
The script exits with code `2` on auth failure (skipped), `1` on validation failure, `0` on success.
Check exit code after running:
- Exit `2` → auth failure: mark status `FAILED — auth error`, tell user "Pass 3 — BAN auth failed. 2/3 passes completed. Submit to BAN manually before portal submission." Do NOT report all passes green.
- Exit `1` → validation issues found: parse `validator-response.json` for issues. **Check `data.specificationPassed`** — if `false`, status is FAILED even if only known exceptions remain. Never report PASSED when `specificationPassed` is false.
- Exit `0` → passed (`specificationPassed: true` and no CRITICAL/HIGH outside known exceptions)

---

## Parse Results

`data.issues[]` — severity: `0=CRITICAL`, `1=HIGH`, `2=MEDIUM`, `3=LOW`

---

## CRITICAL (severity 0) — always auto-fix

**Before auto-fixing any CRITICAL: check `rules.md` Known BAN Exceptions table.**
If the issue matches a known exception → skip auto-fix, record as `KNOWN-EXCEPTION` in report, do not iterate on it.

Batch-fix all remaining CRITICALs. Re-run BAN (max 10 iterations) until CRITICAL count = 0.

| Code | Fix |
|------|-----|
| `E-01-01` | Add `Location` header with `deprecated: false`, `nullable: false`, `pattern`, `minLength`, `maxLength` to 201 response |
| `E-02-02` | Add `^`/`$` anchors; remove `.*`, `.+`, forbidden chars in `[]`, greedy `+`/`*` outside `[]` |
| `type-string` | Two cases: **(A) Field has `enum`** — remove `pattern`, `minLength`, and `maxLength` if present. Enum is the sole constraint; these three fields must not coexist with enum (rules.md enum exemption). **(B) Field has no `enum`** — add only what is missing; never overwrite existing values: `minLength: 0`, `maxLength: 10000`, `pattern: "^[a-zA-Z0-9 .,_-]{0,10000}$"` (from rules.md Step 11 anomaly-fix constants). |
| `type-number` | Add `minimum: 0`, `maximum: 2147483647` |
| `type-array` | Add `minItems: 0`, `maxItems: 100` |
| `data-leakage` | Do NOT auto-fix — raise as Red Flag. See rules.md Sensitive Fields section. |

---

## HIGH (severity 1) — check known exceptions first

**Before showing HIGH issues to user:** check `rules.md` Known BAN Exceptions table.

If issue matches a known exception:
- Skip — do not fix, do not ask user
- Record in report under `#### Known Exceptions` with the documented reason

**Also exempt from user choice — always skip regardless of "fix all":**
- `data-leakage` issues at any severity → raise as Red Flag only, never auto-fix

For remaining HIGH issues (excluding known exceptions and data-leakage), ask user:
> "BAN found {N} HIGH issue(s). How would you like to proceed?
> - **fix all** — auto-fix all
> - **skip all** — review in generation-report.md
> - **choose** — step through each one"

For **choose**: show code, file, line, message. Ask "Fix this? [yes/no]".

After fixing: re-run BAN **once** to confirm (max 1 re-run for HIGH issues — do not loop). Before overwriting `validator-response.json`, store the issues list from the current run in memory. The generation report's "Auto-Fixed" and "Fixed by User Choice" tables must use that stored list — do not re-read `validator-response.json` after the re-run for report purposes. Then overwrite with the new response as the final record.

To suppress a fix permanently: add a row to **`rules.md` Known BAN Exceptions table** (canonical location — never add exceptions here in `ban-validator-guide.md`).

---

## MEDIUM/LOW (severity 2–3) — log only

Record in `validator-response.json` and `generation-report.md`. No user prompt.

---

## Tell User

`"Pass 3 — BAN validation done. CRITICAL: {X} auto-fixed. HIGH: {Y} fixed / {Z} skipped. MEDIUM/LOW: {W} — see generation-report.md."`
