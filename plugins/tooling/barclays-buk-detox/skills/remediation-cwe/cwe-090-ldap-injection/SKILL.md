---
name: cwe-090-ldap-injection
description: "CWE-90: Improper Neutralization of Special Elements used in an LDAP Query ('LDAP Injection') Remediation — Remediate LDAP injection vulnerabilities by properly escaping user input and using parameterized queries."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-90: Improper Neutralization of Special Elements used in an LDAP Query ('LDAP Injection') Remediation
## Quick Start

This skill provides the fix pattern for CWE-90 LDAP Injection. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-90 is classified as LDAP injection in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```

**Note**: This skill addresses **LDAP Injection**. For Expression Language (EL/OGNL/SpEL) injection, see `cwe-917-expression-eval`.

## CWE Information

- **CWE ID**: CWE-90
- **CWE Name**: Improper Neutralization of Special Elements used in an LDAP Query ('LDAP Injection')
- **Severity**: High
- **OWASP Category**: A03:2021 - Injection
- **Reference**: https://cwe.mitre.org/data/definitions/90.html

## Purpose

Remediate LDAP injection vulnerabilities by properly escaping user-supplied data before incorporating it into LDAP queries. LDAP injection allows attackers to:
- **Read sensitive data**: Extract employee records, credentials, or directory information
- **Modify directory data**: Alter LDAP entries (if connection has write permissions)
- **Bypass authentication**: Log in as any user by injecting filter logic
- **Execute code**: In certain LDAP server configurations with dangerous extensions or stored procedures

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-90`.
  - `vulnerability_type` (string, recommended): Should indicate "LDAP Injection" for this skill.

## Steps

1. **Identify LDAP query construction** with user input.
   - Look for `ctx.search()`, `LdapContext`, `SearchControls` with string concatenation.
   - Identify user-controlled data flowing into LDAP filters.

2. **Apply input sanitization and escaping.**
   - Use ESAPI.encoder().encodeForLDAP() for proper RFC 4515 escaping.
   - Alternatively, validate input with strict whitelisting (alphanumeric + allowed symbols).
   - Never directly concatenate user input into LDAP filters.

3. **Apply the edit.**
   - Use `Edit` to add ESAPI encoding before filter concatenation.
   - Ensure all special LDAP characters are escaped: `\`, `*`, `(`, `)`, NUL.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "ldap_filter_escaped": true,
      "method": "esapi | whitelist | validation"
    }
  ],
  "ldap_filters_fixed": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```java
// VULNERABLE: Direct concatenation of user input into LDAP filter
String userInput = request.getParameter("username");
String filter = "(&(objectClass=person)(cn=" + userInput + "))";
SearchControls controls = new SearchControls();
NamingEnumeration<SearchResult> results = ctx.search("", filter, controls);

// Attack: username = "*)(|(cn=*" → filter becomes: "(&(objectClass=person)(cn=*)(|(cn=*))"
// This bypasses authentication by matching any object
```

## Fix Pattern

1. **Preferred: Use ESAPI.encoder().encodeForLDAP()** (OWASP-recommended).
2. **Alternative: Implement RFC 4515 escaping** with explicit character escaping.
3. **Validation: Whitelist input** (alphanumeric + limited symbols) before use.
4. **Never: Directly concatenate user input into LDAP filters.**

## Language-Specific Examples

### Java - LDAP Injection (ESAPI Recommended)

**Before (vulnerable):**
```java
String userInput = request.getParameter("username");
String filter = "(&(objectClass=person)(cn=" + userInput + "))";
SearchControls controls = new SearchControls();
NamingEnumeration<SearchResult> results = ctx.search("", filter, controls);
```

**After (fixed with ESAPI):**
```java
import org.owasp.esapi.ESAPI;

String userInput = request.getParameter("username");
String encodedInput = ESAPI.encoder().encodeForLDAP(userInput);
String filter = "(&(objectClass=person)(cn=" + encodedInput + "))";
SearchControls controls = new SearchControls();
NamingEnumeration<SearchResult> results = ctx.search("", filter, controls);
```

### Java - LDAP Injection (RFC 4515 Escaping Alternative)

**Before (vulnerable):**
```java
String surName = request.getParameter("surname");
String filter = "(" + ATTR_SURNAME + "=" + surName + "*)";
```

**After (fixed with RFC 4515 escaping):**
```java
private String escapeLdapFilterValue(String value) {
    if (value == null) return "";
    StringBuilder sb = new StringBuilder(value.length());
    for (int i = 0; i < value.length(); i++) {
        char c = value.charAt(i);
        switch (c) {
            case '\\': sb.append("\\5c"); break;
            case '*':  sb.append("\\2a"); break;
            case '(':  sb.append("\\28"); break;
            case ')':  sb.append("\\29"); break;
            case '\0': sb.append("\\00"); break;
            default:   sb.append(c);
        }
    }
    return sb.toString();
}

String surName = request.getParameter("surname");
String filter = "(" + ATTR_SURNAME + "=" + escapeLdapFilterValue(surName) + "*)";
```

### Java - LDAP Injection (Whitelist Validation)

**Before (vulnerable):**
```java
String foreName = request.getParameter("foreName");
String surName = request.getParameter("surName");
String filter = "(&(" + ATTR_SURNAME + "=" + surName + "*)(" + ATTR_GIVEN_NAME + "=" + foreName + "*))";
```

**After (fixed with strict whitelist validation):**
```java
private static final Pattern VALID_NAME_PATTERN = Pattern.compile("^[a-zA-Z0-9](?:[._-]?[a-zA-Z0-9])*$");

private boolean isValidLdapInput(String input) {
    return input != null && VALID_NAME_PATTERN.matcher(input).matches();
}

String foreName = request.getParameter("foreName");
String surName = request.getParameter("surName");

if (!isValidLdapInput(surName) || !isValidLdapInput(foreName)) {
    throw new IllegalArgumentException("Invalid input");
}

String filter = "(&(" + ATTR_SURNAME + "=" + surName + "*)(" + ATTR_GIVEN_NAME + "=" + foreName + "*))";
```

### Python - LDAP Injection

**Before (vulnerable):**
```python
from ldap3 import Server, Connection

username = request.args.get('username')
filter_str = f"(&(objectClass=person)(cn={username}))"
conn.search(search_base, filter_str)
```

**After (fixed):**
```python
from ldap3 import Server, Connection
from ldap3.utils.escape import escape_filter_chars

username = request.args.get('username')
escaped_username = escape_filter_chars(username)
filter_str = f"(&(objectClass=person)(cn={escaped_username}))"
conn.search(search_base, filter_str)
```

## Testing Guidance

1. **Test with valid names**: Ensure normal usernames/surnames work correctly.
   - Example: "John", "Smith", "Jean-Paul", "O'Brien"
2. **Test LDAP injection payloads**: Try payloads that should be rejected:
   - `*)(|(cn=*` → Should be escaped to `\2a)(|(cn=*`
   - `*` → Should be escaped to `\2a`
   - `)(objectClass=*` → Should be escaped to `)(objectClass=*`
3. **Verify search results**: Confirm that escaping doesn't break legitimate searches.
4. **Test boundary conditions**: Empty strings, null values, special characters.

## Common Mistakes

1. **Incomplete escaping** - Missing one or more LDAP metacharacters (*, (, ), \, NUL).
2. **Blacklist instead of whitelist** - Blacklists are easy to bypass; use proper escaping.
3. **Double escaping** - Escaping already-escaped input causes data corruption.
4. **Using dangerous libraries** - Don't use LDAP injection-prone libraries without wrapping.
5. **Mixing encoding approaches** - Don't mix ESAPI, RFC 4515, and custom escaping.

## Constraints

- Always escape user input before LDAP filter concatenation.
- Prefer ESAPI.encoder().encodeForLDAP() (OWASP-endorsed).
- If escaping, implement RFC 4515 Section 3 correctly.
- Never trust user input for LDAP queries.
- Validate input format (regex) as defense-in-depth alongside escaping.
- Follow principle of least privilege: LDAP connection should have minimal permissions.

## Distinguishing LDAP Injection from Expression Language Injection

Both CWE-90 and Expression Language injection can occur in enterprise Java applications. This skill covers **LDAP Injection only**. Here's how to distinguish:

| Aspect | LDAP Injection (CWE-90) | Expression Language Injection (CWE-917) |
|--------|------|---------|
| **Attack vector** | LDAP filter concatenation with user input | EL/OGNL/SpEL expression evaluation |
| **Keywords** | `ctx.search()`, `LdapContext`, `SearchControls`, LDAP filters | `parser.parseExpression()`, `ognl.parseExpression()`, template EL |
| **Risk** | Unauthorized directory access, authentication bypass | Remote code execution |
| **Escape method** | RFC 4515 (ESAPI) | N/A (avoid evaluation entirely) |
| **Fix strategy** | Escape metacharacters | Whitelist expressions or avoid eval() |

If the finding involves Spring EL, OGNL, or SpEL, use the `cwe-917-expression-eval` skill instead.

## OWASP & Standards References

- OWASP LDAP Injection Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/LDAP_Injection_Prevention_Cheat_Sheet.html
- RFC 4515: LDAP Search Filter Syntax (Section 3 defines escaping rules)
- ESAPI Java: https://owasp.org/www-project-esapi/

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed as LDAP Injection (not Expression Language injection)
- [ ] Detection: Identified LDAP query construction with user input (ctx.search, SearchControls, filters)
- [ ] Applied ESAPI.encoder().encodeForLDAP() OR RFC 4515 escaping OR strict whitelist validation
- [ ] Language-specific fix pattern applied (Java/Python as available) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
- [ ] If Expression Language injection was misclassified as LDAP, refer to `cwe-917-expression-eval` skill instead
