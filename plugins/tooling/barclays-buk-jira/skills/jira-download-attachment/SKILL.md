---
name: jira-download-attachment
user-invocable: false
description: >
    Use this skill to download and parse the content of a JIRA attachment by ID.
    Supports xlsx/xls (markdown table per sheet), csv (markdown table),
    docx/doc (paragraph text), pdf (extracted text per page),
    json/xml/sql/txt/md/yaml/yml (raw UTF-8), and image files (metadata only).
    Call jira-get-attachments first to discover attachment IDs.
    Trigger when an agent needs the actual content of a file attached to a ticket,
    such as a mapping spreadsheet or requirements document.
---

# JIRA Download Attachment

Download and parse a JIRA attachment by ID. Delegates to `barclays-buk-jira:jira-agent` with `OPERATION=DownloadAttachment`.

## Prerequisites

`JIRA_AUTH_TOKEN` environment variable must be set. For xlsx/xls parsing, `openpyxl` must be installed (`pip install openpyxl`). For docx, `python-docx`. For pdf, `pdfplumber`.

## Invocation

```
OPERATION:     DownloadAttachment
ATTACHMENT_ID: 12345
```

## Supported Formats

| Extension | Output |
|---|---|
| `.xlsx` / `.xls` | Markdown table per sheet |
| `.csv` | Markdown table |
| `.docx` / `.doc` | Extracted paragraph text |
| `.pdf` | Extracted text per page |
| `.json` / `.xml` / `.sql` / `.txt` / `.md` / `.yaml` / `.yml` | Raw UTF-8 text |
| `.png` / `.jpg` / `.jpeg` / `.gif` / `.svg` / `.bmp` | Metadata only (filename, size, MIME type) |
| Other | Unsupported notice with filename and MIME type |

## Output

```json
{
  "filename": "mapping_spec.xlsx",
  "ext": "xlsx",
  "size": 45678,
  "parsed_content": "### Sheet: Mappings\n\n| Source | Target | ...\n..."
}
```

## Agent Self-Check

- [ ] Attachment ID sourced from `jira-get-attachments` output — never invented
- [ ] File downloaded to a temp path and cleaned up after parsing
- [ ] Parse errors reported in `parsed_content` field rather than crashing
- [ ] Missing optional libraries reported with install instructions
