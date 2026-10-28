# Endpoint Extractor — Step 5 Reference

Rules for extracting structured endpoint contracts from an endpoint list.
Referenced by SKILL.md Step 5.

---

## Input Formats

**Inline string:**
```
POST /v1/accounts/open, GET /v1/accounts/{accountId}
```

**JSON array:**
```json
[
  {"method": "POST", "path": "/v1/accounts/open"},
  {"method": "GET", "path": "/v1/accounts/{accountId}"}
]
```

**Excel table (extracted text):** Look for columns named Method, Path, Description, Summary, Tag, OperationId (case-insensitive).

**Design doc section:** Look for tables or lists of API endpoints under the named section.

---

## Output Shape

Produce this JSON array internally (do not show to user):

```json
[
  {
    "method": "POST",
    "path": "/v1/accounts/open",
    "operationId": "openAccount",
    "summary": "Open a new credit card account",
    "description": "Opens a new credit card account.",
    "tags": ["accounts"],
    "request_body": {
      "description": "Account opening request payload",
      "required": true,
      "schema_hint": "OpenAccountRequest"
    },
    "responses": [
      {"code": "201", "description": "Account opened", "schema_hint": "OpenAccountResponse"},
      {"code": "400", "description": "Validation failure", "schema_hint": "ErrorResponse"},
      {"code": "401", "description": "Unauthenticated", "schema_hint": "ErrorResponse"},
      {"code": "403", "description": "Unauthorised", "schema_hint": "ErrorResponse"},
      {"code": "404", "description": "Not found", "schema_hint": "ErrorResponse"},
      {"code": "429", "description": "Too many requests", "schema_hint": "ErrorResponse"},
      {"code": "500", "description": "Internal server error", "schema_hint": "ErrorResponse"},
      {"code": "503", "description": "Service unavailable", "schema_hint": "ErrorResponse"}
    ],
    "path_params": [],
    "query_params": []
  }
]
```

---

## Determinism Rule — Same Input Must Produce Same Output

When extracting from free-text sources (design docs, Confluence, Excel, plain text), the same document can yield different endpoints on different runs if the language is ambiguous (e.g. "create account" vs "open account" both present in the same doc).

To prevent this:
- **When multiple candidate paths are found**, always pick the **most specific** one (longest path, most path segments). Never silently alternate between candidates.
- **When the document uses both a technical path and a business description**, the technical path takes precedence.
- **When extraction is ambiguous**, ask the user once and cache the answer — do NOT re-ask on subsequent extractions from the same document.
- **Recommended**: use `api-config.yaml` `endpoints` field to lock endpoints for the project — bypasses extraction entirely.

---

## Extraction Rules

1. **Standard error responses:** Always include 400, 401, 403, 404, 429, 500, 503 — add any missing ones.
   **Non-standard responses (409, 422, 502, 504 etc.):** Only include if explicitly mentioned in the input document. Do NOT add them by default.

2. **operationId derivation:** Build as `{leading-verb}{Resource}By{Params}`:

   **Step 1 — Determine the leading verb:**
   - If the last path segment is itself a verb word (`open`, `close`, `freeze`, `cancel`, `activate`, `validate`, `submit`, `approve`, `reject`, `retry`) → use that segment as the leading verb
   - Otherwise → use the HTTP method as the leading verb (`get`, `post`, `put`, `patch`, `delete`)

   **Step 2 — Build the remainder:**
   - Take all non-verb path segments (excluding version prefix `/v1/` etc. and path params)
   - PascalCase each segment preserving its exact plural/singular form (e.g. `accounts` → `Accounts`, `transactions` → `Transactions`) — never singularise or pluralise
   - PascalCase them in order, append `By{ParamName}` for each path param in order
   - For `GET /v1/accounts/{accountId}/transactions/{transactionId}`: resource = `AccountTransaction`, params = `ByAccountIdByTransactionId` → `getAccountTransactionByAccountIdByTransactionId`

   **Examples:**
   - `POST /v1/accounts/open` → verb=`open`, resource=`Account` → `openAccount`
   - `GET /v1/accounts/{accountId}` → verb=`get`, resource=`Accounts`, param=`AccountId` → `getAccountsByAccountId`
   - `DELETE /v1/accounts/{accountId}/freeze` → verb=`freeze` (last segment is a verb), resource=`Account`, param=`AccountId` → `freezeAccountByAccountId`
   - `POST /v1/payments/validate` → verb=`validate`, resource=`Payment` → `validatePayment`
   - `GET /v1/accounts` → verb=`get`, resource=`Accounts` → `getAccounts`

3. **Tags:** First path segment after version prefix, lowercase and exact form: `/v1/accounts/...` → `"accounts"`. Use provided tag if given, lowercased.

4. **Request body:**
   - GET, DELETE, HEAD → `request_body: null`
   - POST, PUT, PATCH → `request_body: { required: true }` unless source explicitly says optional

5. **Response code for POST:**
   - POST that **creates a new resource** (operationId starts with `create`, `open`, `add`, `register`, `submit`, `enrol`) → `201` + `Location` header
   - POST that **queries, validates, or processes without creating** (operationId starts with `validate`, `search`, `find`, `calculate`, `check`, `verify`, `get`) → `200` (no Location header — do not apply G11)
   - POST that **starts an async/long-running process** and source specifies async behaviour (operationId starts with `process`, `dispatch`, `enqueue`, or source says "async"/"asynchronous") → `202 Accepted` (no Location header)
   - If ambiguous → use `201` and add Red Flag: "Verify correct response code — 200 vs 201 vs 202"

6. **PATCH method rules:**
   - Request body: required (partial update — only fields being changed)
   - Response code: `200` (returns updated resource) or `204` (no content returned) — use `200` unless source specifies otherwise
   - No `Location` header — PATCH modifies existing resource, does not create new
   - operationId: use `patch` as leading verb unless last path segment is a verb (e.g. `PATCH /v1/accounts/{id}/freeze` → `freezeAccountById`)
   - Semantics: partial update per RFC 7396 — request body contains only changed fields, not full resource

7. **PUT method rules:**
   - Request body: required (full resource replacement)
   - Response code: `200` (returns replaced resource) or `204`
   - No `Location` header
   - operationId: use `replace` as leading verb (e.g. `PUT /v1/accounts/{id}` → `replaceAccountById`) or `update` if source uses that terminology

8. **schema_hint:** PascalCase derived from operationId + "Request"/"Response" — used by component builder to name schema files.

9. **Config override:** If `api-config.yaml` specifies a response code for an endpoint (via domain rules), apply it. Input source description of expected response code also takes priority over the defaults in rules 5–7 above.
