#!/usr/bin/env python3
"""
Backstage Catalogue Lookup — Layer 1 API candidate search.

Usage:
    python backstage_lookup.py <query> [--domain <domain>] [--api-type <pAPI|iAPI|sAPI|xAPI>]
                                        [--top <N>] [--json]

Parses reference/backstage_catalogue_index.md (sibling to this scripts/ directory)
and returns the top-N ranked candidates matching the query.

Scoring uses keyword overlap across: name, title, description, tags, domain.
No external dependencies — stdlib only.

Examples:
    python backstage_lookup.py "customer retrieve personal details"
    python backstage_lookup.py "customer" --api-type pAPI --top 5
    python backstage_lookup.py "account balance" --domain buk/buk-domain-current-account --json
"""

import re, json, sys, argparse
from pathlib import Path

# Location of the catalogue relative to this script
_SCRIPT_DIR   = Path(__file__).resolve().parent
_SKILL_DIR    = _SCRIPT_DIR.parent
_CATALOGUE    = _SKILL_DIR / 'reference' / 'backstage_catalogue_index.md'

# API-type name patterns used in component names/titles
_API_TYPE_RE = {
    'pAPI': re.compile(r'\bpAPI\b', re.IGNORECASE),
    'iAPI': re.compile(r'\biAPI\b', re.IGNORECASE),
    'sAPI': re.compile(r'\bsAPI\b', re.IGNORECASE),
    'xAPI': re.compile(r'\bxAPI\b', re.IGNORECASE),
}


def _parse_catalogue(path):
    """Parse the markdown component table in backstage_catalogue_index.md.

    Returns a list of dicts with keys:
      name, title, system, domain, tags, description, confluence_url, gitlab_slug
    """
    components = []
    in_table   = False
    header_seen = False

    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.rstrip('\n')

            # Detect start of Component Catalogue table
            if '## Component Catalogue' in line:
                in_table = True
                header_seen = False
                continue

            if not in_table:
                continue

            # Skip non-table lines once inside the table
            if not line.startswith('|'):
                if components:   # first non-table line after table rows → done
                    break
                continue

            cells = [c.strip() for c in line.split('|')[1:-1]]

            # Skip header row and separator row
            if not header_seen:
                if cells and cells[0].lower() == 'name':
                    header_seen = True
                continue
            if cells and re.fullmatch(r'[-: ]+', cells[0]):
                continue

            # Pad to expected width
            while len(cells) < 8:
                cells.append('')

            components.append({
                'name':           cells[0],
                'title':          cells[1],
                'system':         cells[2],
                'domain':         cells[3],
                'tags':           cells[4],
                'description':    cells[5],
                'confluence_url': cells[6],
                'gitlab_slug':    cells[7],
            })

    return components


def _detect_api_type(component):
    """Detect the API type from name or title."""
    text = f"{component['name']} {component['title']}"
    for api_type, pattern in _API_TYPE_RE.items():
        if pattern.search(text):
            return api_type
    # Fall back to suffix detection in the name
    name = component['name'].lower()
    for suffix in ('papi', 'iapi', 'sapi', 'xapi'):
        if name.endswith(f'-{suffix}') or name.endswith(suffix):
            return suffix.upper()[:1] + 'API'
    return None


def _tokenize(text):
    """Split text into lowercase word tokens."""
    return set(re.findall(r'[a-z0-9]+', text.lower()))


def _score(component, query_tokens, api_type_filter=None, domain_filter=None):
    """Score a component against query tokens. Returns float 0..1."""
    # Apply hard filters first
    if api_type_filter:
        comp_type = _detect_api_type(component)
        if comp_type and comp_type.lower() != api_type_filter.lower():
            return 0.0

    if domain_filter and domain_filter.lower() not in component['domain'].lower():
        return 0.0

    # Build searchable token sets with field weights
    weighted_fields = [
        (component['name'],        3.0),
        (component['title'],       2.5),
        (component['description'], 1.5),
        (component['tags'],        1.0),
        (component['domain'],      0.5),
    ]

    total_weight  = 0.0
    matched_weight = 0.0
    for text, weight in weighted_fields:
        tokens = _tokenize(text)
        if not tokens:
            continue
        overlap = len(query_tokens & tokens)
        if overlap:
            # Partial credit proportional to fraction of query tokens matched in this field
            credit = overlap / len(query_tokens) * weight
            matched_weight += credit
        total_weight += weight

    return matched_weight / total_weight if total_weight else 0.0


def search(query, api_type_filter=None, domain_filter=None, top_n=10, catalogue_path=None):
    """Search the Backstage catalogue and return ranked candidates.

    Args:
        query:          Free-text search string
        api_type_filter: e.g. "pAPI", "iAPI" — filter by API type
        domain_filter:  e.g. "buk-domain-current-account" — substring match against domain
        top_n:          Maximum number of results to return
        catalogue_path: Override default catalogue path (for testing)

    Returns:
        list of dicts: {"rank": int, "score": float, "api_type": str, ...component fields...}
    """
    path = Path(catalogue_path) if catalogue_path else _CATALOGUE
    if not path.exists():
        raise FileNotFoundError(
            f"Backstage catalogue not found at {path}. "
            "Ensure the mts-reference skill is properly installed."
        )

    components   = _parse_catalogue(path)
    query_tokens = _tokenize(query)

    if not query_tokens:
        raise ValueError("Query is empty after tokenization.")

    scored = []
    for comp in components:
        s = _score(comp, query_tokens, api_type_filter, domain_filter)
        if s > 0:
            scored.append((s, comp))

    scored.sort(key=lambda x: -x[0])
    results = []
    for rank, (score, comp) in enumerate(scored[:top_n], start=1):
        results.append({
            'rank':          rank,
            'score':         round(score, 4),
            'api_type':      _detect_api_type(comp) or 'unknown',
            **comp,
        })
    return results


def _print_text(results, query):
    if not results:
        print(f'No matches found for: "{query}"')
        return
    print(f'Top {len(results)} matches for: "{query}"\n')
    for r in results:
        print(f"  #{r['rank']} [{r['api_type']}] {r['name']}")
        print(f"     Title:  {r['title']}")
        if r['domain']:
            print(f"     Domain: {r['domain']}")
        if r['description']:
            desc = r['description'][:120] + ('...' if len(r['description']) > 120 else '')
            print(f"     Desc:   {desc}")
        if r['confluence_url']:
            print(f"     Confluence: {r['confluence_url']}")
        print(f"     Score: {r['score']}")
        print()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('query', help='Search keywords (free text)')
    parser.add_argument('--domain',   metavar='DOMAIN',   help='Filter by domain substring (e.g. buk-domain-current-account)')
    parser.add_argument('--api-type', metavar='TYPE',     help='Filter by API type: pAPI, iAPI, sAPI, xAPI')
    parser.add_argument('--top',      metavar='N', type=int, default=10, help='Maximum results to return (default: 10)')
    parser.add_argument('--json',     action='store_true', help='Output JSON instead of human-readable text')
    args = parser.parse_args()

    try:
        results = search(
            query=args.query,
            api_type_filter=getattr(args, 'api_type', None),
            domain_filter=args.domain,
            top_n=args.top,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        _print_text(results, args.query)


if __name__ == '__main__':
    main()
