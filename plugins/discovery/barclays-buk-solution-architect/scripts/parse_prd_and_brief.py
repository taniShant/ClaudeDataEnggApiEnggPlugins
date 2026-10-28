#!/usr/bin/env python3
"""
Deterministic PRD and Brief parser for requirements understanding.

This script reads PRD and optional Brief markdown files and produces
requirements.json — a source-neutral intermediate matching the schema
used by Jira requirements retrieval.

Responsibilities (deterministic only):
- Read markdown files
- Extract sections by heading level
- Preserve native identifiers (FR-1, FR-2, etc.)
- Generate evidence units with source-native IDs
- Produce file hashes (SHA-256)
- Output requirements.json

NO semantic interpretation — that belongs in the LLM reasoning stage.

Usage:
    python parse_prd_and_brief.py \\
      --prd-path prd.md \\
      --brief-path brief.md (optional) \\
      --invocation-dir /path/to/work

Output:
    <output_dir>/requirements/<identifier>.json
    Format: same schema as Jira requirements.json (v1.0)
    with source.type = "prd" or "brief" instead of "jira"
"""

import sys
import os
import re
import json
import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

try:
    if sys.stdout and hasattr(sys.stdout, 'buffer') and sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    if sys.stderr and hasattr(sys.stderr, 'buffer') and sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
except (AttributeError, OSError):
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_title_and_meta(content: str) -> Tuple[str, Dict[str, str]]:
    """
    Extract YAML frontmatter and title from markdown.

    Returns (title, metadata_dict).
    """
    # Extract YAML frontmatter if present
    if content.startswith("---"):
        match = re.match(r'---\n(.*?)\n---\n', content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            metadata = {}
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"\'')
            return metadata.get('title', 'Untitled'), metadata

    # Fallback: extract first h1 heading as title
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = match.group(1) if match else "Untitled"
    return title, {}


def extract_sections(content: str, source_type: str) -> Dict[str, List[str]]:
    """
    Extract sections from markdown by heading level.

    Returns dict mapping section_name -> list of content units.
    """
    sections: Dict[str, List[str]] = {}
    lines = content.split('\n')
    current_section = None
    current_content = []

    for line in lines:
        # Detect level-2 headers (## — main sections)
        if line.startswith('## '):
            # Flush previous section
            if current_section and current_content:
                content_text = '\n'.join(current_content).strip()
                if content_text:
                    if current_section not in sections:
                        sections[current_section] = []
                    sections[current_section].append(content_text)

            section_title = line[3:].strip()
            current_section = _normalize_section_name(section_title)
            current_content = []

        elif current_section is not None:
            # Collect content for current section
            current_content.append(line)

    # Flush final section
    if current_section and current_content:
        content_text = '\n'.join(current_content).strip()
        if content_text:
            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append(content_text)

    return sections


def _normalize_section_name(title: str) -> str:
    """Convert section title to normalized key."""
    # Remove leading numbers and dots
    normalized = re.sub(r'^\d+\.\s*', '', title)
    # Convert to snake_case
    normalized = re.sub(r'\s+', '_', normalized.lower())
    # Remove special chars
    normalized = re.sub(r'[^\w_]', '', normalized)
    return normalized or 'section'


def extract_functional_requirements(content: str) -> Dict[str, str]:
    """
    Extract FR-N identifiers and descriptions from PRD sections.

    Formats supported:
    - Heading format: #### FR-1: Description (as in features section)
    - Bold format: **FR-1:** Description (as in success metrics section)

    Returns dict: {"FR-1": "Description...", "FR-2": "..."}
    """
    reqs = {}

    # Match both header format (#### FR-N:) and bold format (**FR-N:**)
    # Pattern 1: Heading format (#### FR-N: Description)
    pattern_heading = r'^#+\s*([A-Z]+-\d+)\s*:\s*(.+?)$'
    for match in re.finditer(pattern_heading, content, re.MULTILINE):
        req_id = match.group(1)
        req_text = match.group(2).strip()
        # Clean up markdown formatting and collapse whitespace
        req_text = re.sub(r'\*+', '', req_text)  # Remove asterisks
        req_text = re.sub(r'\s+', ' ', req_text)  # Collapse whitespace
        reqs[req_id] = req_text

    # Pattern 2: Bold format (**FR-N:** Description) - for non-heading formatted requirements
    # Only add if not already captured from heading format
    pattern_bold = r'\*\*([A-Z]+-\d+)\s*:\s*\*?\*?(.+?)(?=\*\*[A-Z]+-\d+|$)'
    for match in re.finditer(pattern_bold, content, re.DOTALL):
        req_id = match.group(1)
        if req_id not in reqs:  # Don't overwrite heading-formatted entries
            req_text = match.group(2).strip()
            # Clean up markdown formatting and collapse whitespace
            req_text = re.sub(r'\*+', '', req_text)  # Remove asterisks
            req_text = re.sub(r'\s+', ' ', req_text)  # Collapse whitespace
            reqs[req_id] = req_text

    return reqs


def build_evidence_units_for_prd(sections: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Build evidence units from extracted PRD sections.

    Uses source-native IDs: FR-1, FR-2, etc.
    Format: {id: "functional_requirements:FR-1", section: "functional_requirements", source_value: "..."}
    """
    units = []

    # Build combined content for all sections to search for requirements
    all_content = '\n'.join('\n'.join(v) for v in sections.values())

    # Process functional requirements (search across all content for FR-N patterns)
    reqs = extract_functional_requirements(all_content)
    for req_id, req_text in reqs.items():
        units.append({
            'id': f'functional_requirements:{req_id}',
            'source_native_id': req_id,
            'prd_section': 'features',
            'source_value': req_text
        })

    # Process non-goals section if present
    for section_key in ('non_goals', 'non_goal', 'non-goals'):
        if section_key in sections:
            ng_content = '\n'.join(sections[section_key])
            if ng_content.strip():
                units.append({
                    'id': 'non_goals:0',
                    'source_native_id': None,
                    'prd_section': 'non_goals',
                    'source_value': ng_content
                })
            break

    # Process assumptions section if present
    for section_key in ('assumptions', 'assumption'):
        if section_key in sections:
            assumptions_content = '\n'.join(sections[section_key])
            if assumptions_content.strip():
                units.append({
                    'id': 'assumptions:0',
                    'source_native_id': None,
                    'prd_section': 'assumptions',
                    'source_value': assumptions_content
                })
            break

    # Process constraints/dependencies section if present
    for section_key in ('integration', 'dependencies', 'constraints'):
        if section_key in sections:
            dep_content = '\n'.join(sections[section_key])
            if dep_content.strip():
                units.append({
                    'id': f'{section_key}:0',
                    'source_native_id': None,
                    'prd_section': section_key,
                    'source_value': dep_content
                })
            break

    return units


def build_evidence_units_for_brief(content: str) -> List[Dict[str, Any]]:
    """
    Build evidence units from Brief markdown.

    Uses positional IDs: problem:0, solution:0, scope:0, etc.
    """
    units = []
    sections = extract_sections(content, 'brief')

    for section_key in ['problem', 'solution', 'scope', 'success_criteria', 'vision']:
        if section_key in sections:
            for i, section_content in enumerate(sections[section_key]):
                units.append({
                    'id': f'{section_key}:{i}',
                    'source_native_id': None,
                    'brief_section': section_key,
                    'source_value': section_content
                })

    return units


def parse_prd_and_brief(
    prd_path: Optional[Path],
    brief_path: Optional[Path]
) -> Tuple[Dict[str, Any], str, Dict[str, str]]:
    """
    Parse PRD and optional Brief, return normalized evidence structure.

    Returns:
        (normalized_evidence, source_identifier, hashes)

    normalized_evidence has structure matching Jira requirements extraction:
        {
            "source_type": "prd",
            "prd_path": "...",
            "prd_content": "...",
            "brief_path": "...",
            "brief_content": "...",
            "summary": "...",
            "description": "...",
            "evidence_units": [...]
        }
    """
    if not prd_path:
        raise ValueError("PRD path required")

    prd_path = Path(prd_path)
    if not prd_path.exists():
        raise FileNotFoundError(f"PRD not found: {prd_path}")

    prd_content = prd_path.read_text(encoding='utf-8')
    prd_hash = hashlib.sha256(prd_content.encode()).hexdigest()
    prd_title, prd_meta = extract_title_and_meta(prd_content)

    brief_content = None
    brief_hash = None
    brief_title = None

    if brief_path:
        brief_path = Path(brief_path)
        if brief_path.exists():
            brief_content = brief_path.read_text(encoding='utf-8')
            brief_hash = hashlib.sha256(brief_content.encode()).hexdigest()
            brief_title, _ = extract_title_and_meta(brief_content)

    # Extract evidence units from both sources
    prd_units = build_evidence_units_for_prd(extract_sections(prd_content, 'prd'))
    brief_units = build_evidence_units_for_brief(brief_content) if brief_content else []

    # Build combined normalized evidence
    normalized_evidence = {
        'source_type': 'prd',
        'prd_path': str(prd_path),
        'prd_hash': prd_hash,
        'brief_path': str(brief_path) if brief_path else None,
        'brief_hash': brief_hash,
        'summary': prd_title,
        'description': prd_content[:500],  # First 500 chars as description
        'prd_sections': extract_sections(prd_content, 'prd'),
        'brief_sections': extract_sections(brief_content, 'brief') if brief_content else {},
        'evidence_units': prd_units + brief_units,
    }

    source_identifier = prd_path.stem
    hashes = {
        'prd_sha256': prd_hash,
        'brief_sha256': brief_hash,
    }

    return normalized_evidence, source_identifier, hashes


def build_requirements_json(
    normalized_evidence: Dict[str, Any],
    source_identifier: str,
    hashes: Dict[str, str],
    prd_path: Path,
    brief_path: Optional[Path]
) -> Dict[str, Any]:
    """
    Build requirements.json output (intermediate format).

    Matches the schema used by Jira retrieval, but with PRD/Brief source.
    """
    now = datetime.now(timezone.utc)

    source_dict = {
        'type': 'prd',
        'prd_path': str(prd_path),
        'prd_sha256': hashes['prd_sha256'],
        'brief_path': str(brief_path) if brief_path else None,
        'brief_sha256': hashes['brief_sha256'],
        'parsed_at': now.isoformat(),
        'endpoint': 'local-prd-parser',
    }

    return {
        'schema_version': '1.0',
        'source': source_dict,
        'requirements': {
            'summary': normalized_evidence['summary'],
            'description': normalized_evidence['description'],
            'type': 'Product Requirement Document',
            'status': 'Inferred',
            'labels': ['prd', 'multi-lender-comparison'],
            'components': [],
            'linked_issues': [],
            'acceptance_criteria': [],
            'evidence_units': normalized_evidence['evidence_units'],
            'evidence_sources': {
                'prd': normalized_evidence.get('prd_sections', {}),
                'brief': normalized_evidence.get('brief_sections', {}),
            }
        },
        'warnings': [
            'PRD parsed deterministically. Semantic interpretation performed by LLM.',
            'Source-native identifiers (FR-1, FR-2, etc.) preserved from PRD.',
        ]
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Parse PRD and optional Brief markdown into requirements.json'
    )
    parser.add_argument(
        '--prd-path', required=True,
        help='Path to PRD markdown file'
    )
    parser.add_argument(
        '--brief-path', default=None,
        help='Path to optional Brief markdown file'
    )
    parser.add_argument(
        '--invocation-dir', required=True,
        help='User invocation directory (for output placement)'
    )

    args = parser.parse_args()

    try:
        prd_path = Path(args.prd_path)
        brief_path = Path(args.brief_path) if args.brief_path else None
        invocation_dir = Path(args.invocation_dir).resolve()

        print("=== PRD/BRIEF PARSING ===", file=sys.stderr)
        print(f"PRD: {prd_path}", file=sys.stderr)
        print(f"Brief: {brief_path if brief_path else '(none)'}", file=sys.stderr)

        # Parse PRD and Brief
        normalized_evidence, source_id, hashes = parse_prd_and_brief(prd_path, brief_path)

        print(f"[OK] PRD parsed successfully", file=sys.stderr)
        print(f"[OK] Evidence units extracted: {len(normalized_evidence['evidence_units'])}", file=sys.stderr)

        # Build requirements.json
        req_json = build_requirements_json(normalized_evidence, source_id, hashes, prd_path, brief_path)

        # Write to output (PRD/Brief use root-level directories, not issue_key subdirs)
        req_dir = invocation_dir / 'requirements'
        req_dir.mkdir(parents=True, exist_ok=True)
        req_file = req_dir / f'{source_id}.json'

        req_file.write_text(json.dumps(req_json, indent=2, ensure_ascii=False), encoding='utf-8')

        print(f"[OK] Written to: {req_file.relative_to(invocation_dir)}", file=sys.stderr)

        # Output summary to stdout
        output = {
            'source_identifier': source_id,
            'prd_path': str(prd_path),
            'brief_path': str(brief_path) if brief_path else None,
            'prd_sha256': hashes['prd_sha256'],
            'brief_sha256': hashes['brief_sha256'],
            'evidence_units_count': len(normalized_evidence['evidence_units']),
            'output_path': str(req_file),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"\n[OK] Parsing complete", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
