#!/usr/bin/env python3
"""
Torch — BM25-style router.

Reads JSON from stdin:
  {"prompt": "<text>", "session_state": {"suppressed": [], "recent": []}}

Writes JSON to stdout:
  {"match": true/false, "candidates": [{"capability_id": "...", "score": 0.0, "command": "...", "one_liner": "...", "install_info": "..."}]}

Environment:
  CLAUDE_PLUGIN_ROOT — base directory of the plugin (default: ".")
"""
import json
import math
import os
import re
import sys

# ---------------------------------------------------------------------------
# Constants — must match compile.py exactly
# ---------------------------------------------------------------------------

ROUTING_TERM_MIN_LEN = 3

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "are", "can", "not",
    "use", "when", "your", "will", "you", "all", "any", "from", "has",
    "its", "was", "but", "have", "been", "into", "their", "would", "also",
}

SCORE_THRESHOLD = float(os.environ.get("DISCOVERY_SCORE_THRESHOLD", "0.18"))
DISCOVERY_PROFILE = os.environ.get("DISCOVERY_PROFILE", "all")
SIGNAL_BONUS = 0.2
NEGATIVE_PENALTY = 0.5
RECENCY_PRIOR = 0.1
TOP_N = int(os.environ.get("DISCOVERY_TOP_N", "3"))

# IDF for tokens not in the index. Treats unknown words as moderately informative —
# higher than the most frequent indexed tokens (~2.3 avg) but below the max (3.3).
# Calibrated so trivial 1-token matches stay below SCORE_THRESHOLD while legitimate
# multi-token matches in longer prompts remain above it.
DEFAULT_IDF = 3.5

# Field weights for BM25 scoring when token_fields present in routing-index.
# Matches in high-signal fields (capability name, precise triggers) contribute more
# than matches in descriptive prose (one_liner).
FIELD_WEIGHTS = {
    "name": 4.0, "triggers": 3.0, "when_short": 2.0, "one_liner": 1.0,
    "action_verb": 5.0,   # Precise intent verb; highest signal
}


def _tokenise(text: str) -> list:
    """Split text into lowercase tokens, filtering stopwords and short tokens.

    Uses a hybrid approach: lowercase-first preserves combined forms (e.g. 'swiftui')
    while camelCase-split tokens are added as extras (e.g. 'SwiftUI' also yields 'swift').
    This keeps index compatibility while enabling code-identifier matching.
    """
    # Primary: lowercase first → preserves combined identifiers like 'swiftui'
    raw = re.split(r'[\s\-_/.,;:!?()\[\]{}]+', text.lower())
    combined = [t for t in raw if len(t) >= ROUTING_TERM_MIN_LEN and t not in STOPWORDS]
    # Supplementary: camelCase-split before lowercasing (handles 'SwiftUI', 'findUserById')
    text_cc = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text_cc = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text_cc)
    raw_cc = re.split(r'[\s\-_/.,;:!?()\[\]{}]+', text_cc.lower())
    seen = set(combined)
    extra = [t for t in raw_cc if len(t) >= ROUTING_TERM_MIN_LEN and t not in STOPWORDS and t not in seen]
    return combined + extra


SYNONYM_GROUPS = [
    {"get", "fetch", "retrieve", "read", "show", "view", "inspect", "check"},
    {"list", "search", "find", "query", "browse", "discover"},
    {"create", "scaffold", "generate", "build", "make", "bootstrap", "init"},
    {"update", "edit", "modify", "patch", "change", "fix", "remediate"},
    {"delete", "remove", "destroy", "drop", "clean"},
    {"scan", "analyze", "assess", "evaluate", "review", "audit", "investigate"},
    {"monitor", "observe", "track", "watch", "alert"},
    {"migrate", "upgrade", "modernize", "refactor", "strangler"},
    {"secure", "harden", "protect", "remediate", "patch", "detox"},
    {"test", "verify", "validate", "check", "probe", "assert"},
    {"deploy", "release", "ship", "publish", "promote"},
    {"document", "describe", "annotate", "explain"},
    {"incident", "outage", "downtime", "pagerduty", "page", "oncall"},
    {"plan", "design", "architect", "strategy"},           # planning intent
    {"implement", "instrument", "wire", "integrate"},      # implementation intent
]

_SYNONYM_MAP: dict = {}
for _group in SYNONYM_GROUPS:
    for _word in _group:
        _SYNONYM_MAP[_word] = _group


def _expand_tokens(tokens: list) -> list:
    """Return (token, weight) pairs including synonyms at 0.3× weight.

    Synonyms act as boosters when direct matches already exist, not as standalone
    signals — 0.3× ensures they can't push an otherwise-irrelevant capability above
    SCORE_THRESHOLD on their own, but do add meaningful weight alongside direct hits.
    """
    result = []
    seen: set = set()
    for t in tokens:
        if t not in seen:
            result.append((t, 1.0))
            seen.add(t)
        for syn in _SYNONYM_MAP.get(t, set()):
            if syn != t and syn not in seen:
                result.append((syn, 0.3))
                seen.add(syn)
    return result


def matches_profile(cap: dict) -> bool:
    """Return True if the capability's audience includes DISCOVERY_PROFILE or 'all'."""
    audience = cap.get("audience", ["all"])
    return "all" in audience or DISCOVERY_PROFILE in audience


def levenshtein(a: str, b: str) -> int:
    """Single-row DP Levenshtein distance, O(min(len_a, len_b)) space."""
    if len(a) < len(b):
        a, b = b, a
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev = i
        for j, cb in enumerate(b, 1):
            curr = min(row[j - 1] + (ca != cb), row[j] + 1, prev + 1)
            row[j - 1] = prev
            prev = curr
        row[len(b)] = prev
    return row[len(b)]


def fuzzy_expand_tokens(tokens: list, all_trigger_terms: set) -> list:
    """Return trigger terms within edit-distance of any prompt token.

    Only called as a fallback when zero candidates pass SCORE_THRESHOLD.
    Max edit distance: 2 for tokens ≥8 chars, 1 for 4–7 chars.
    Additional guards: first 3 chars must match (typos rarely shift early chars);
    substring/extension relationships are skipped (different words, not typos).
    Tokens already present in the index are skipped (they would have matched normally).
    """
    expanded = []
    seen: set = set()
    for t in tokens:
        if len(t) < 4 or t in all_trigger_terms:
            continue
        max_dist = 2 if len(t) >= 8 else 1
        candidates = [
            (levenshtein(t, term), term)
            for term in all_trigger_terms
            if abs(len(t) - len(term)) <= max_dist
            # First-3-char prefix must match (typos rarely shift early chars)
            and t[:3] == term[:3]
            # Skip substring/extension relationships (different words, not typos)
            and not term.startswith(t) and not t.startswith(term)
        ]
        if not candidates:
            continue
        best_dist, best_term = min(candidates)
        if best_dist <= max_dist and best_term not in seen:
            expanded.append(best_term)
            seen.add(best_term)
    return expanded


def _load_index(plugin_root: str) -> dict:
    """Load routing-index.json; return empty structure on any error."""
    index_path = os.path.join(
        plugin_root, "skills", "on", "catalog", "landscape", "routing-index.json"
    )
    try:
        with open(index_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def _load_graph_chains(plugin_root: str) -> dict:
    """
    Load graph-data.json and return a precedes lookup: cap_id → [next_cap_id, ...].
    Returns {} on any error (fail-open — chain hints are advisory).
    """
    graph_path = os.path.join(
        plugin_root, "skills", "on", "catalog", "landscape", "graph-data.json"
    )
    try:
        with open(graph_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        precedes_map: dict = {}
        for edge in data.get("edges", {}).get("precedes", []):
            src = edge.get("from", "")
            dst = edge.get("to", "")
            if src and dst:
                precedes_map.setdefault(src, [])
                if dst not in precedes_map[src]:
                    precedes_map[src].append(dst)
        return precedes_map
    except Exception:
        return {}


def _build_chain_str(start_id: str, precedes_map: dict, capabilities: dict, max_depth: int = 3) -> str:
    """Follow precedes edges from start_id and return a chain hint string."""
    parts = []
    current = start_id
    visited = {current}
    for _ in range(max_depth):
        nexts = precedes_map.get(current, [])
        if not nexts:
            break
        next_id = nexts[0]
        if next_id in visited:
            break
        next_cmd = capabilities.get(next_id, {}).get("command", "")
        if next_cmd and next_cmd != "N/A":
            parts.append(next_cmd)
        visited.add(next_id)
        current = next_id
    return " → ".join(parts)


def _build_predecessor_str(cap_id: str, forward_map: dict, backward_map: dict,
                           capabilities: dict, max_depth: int = 3) -> str:
    """Build backward chain hint for terminal nodes (no forward successors)."""
    preds = backward_map.get(cap_id, [])
    if not preds:
        return ""

    def _short(cid: str) -> str:
        cmd = capabilities.get(cid, {}).get("command", "")
        if cmd and cmd != "N/A":
            return cmd.rsplit(":", 1)[-1]
        return ""

    if len(preds) == 1:
        # Single predecessor: follow backward recursively, then reverse to execution order
        chain = []
        current = preds[0]
        visited = {cap_id}
        for _ in range(max_depth):
            if current in visited:
                break
            label = _short(current)
            if label:
                chain.append(label)
            visited.add(current)
            back = backward_map.get(current, [])
            if len(back) != 1:
                break
            current = back[0]
        chain.reverse()
        return " → ".join(chain) if chain else ""

    # Multiple predecessors (fan-in): list actionable commands
    labels = [_short(p) for p in preds if _short(p)]
    if not labels:
        return ""
    if len(labels) <= 2:
        return ", ".join(labels)
    return ", ".join(labels[:2]) + f" (+{len(labels) - 2} more)"


def _empty_response() -> dict:
    return {"match": False, "candidates": []}


def _apply_diversity_penalty(candidates: list) -> list:
    """Penalize 3rd+ result from the same domain to improve cross-domain diversity.

    First two occurrences per domain are un-penalized; 3rd+ gets ×0.7.
    (Synthesis description: "3rd+ same-domain: ×0.7".)
    """
    domain_count: dict = {}
    result = []
    for c in candidates:  # already sorted by score descending
        domain = c.get("domain", "") or "unknown"
        count = domain_count.get(domain, 0)
        if count >= 2:
            c = {**c, "score": round(c["score"] * 0.7, 4)}
        domain_count[domain] = count + 1
        result.append(c)
    return sorted(result, key=lambda x: (-x["score"], x["capability_id"]))


def score_candidates(prompt: str, session_state: dict, index: dict, graph_chains: dict = None) -> list:
    """Return scored candidates list, sorted descending by score."""
    capabilities = index.get("capabilities", {})
    term_index = index.get("term_index", {})
    idf_index = index.get("idf_index", {})
    bigram_index = index.get("bigram_index", {})

    # Build backward map for predecessor hints on terminal nodes
    backward_map = {}
    if graph_chains:
        for src, dsts in graph_chains.items():
            for dst in dsts:
                backward_map.setdefault(dst, []).append(src)

    if not capabilities:
        return []

    # Ordered token list for bigram extraction; set for O(1) unigram lookup
    prompt_token_list = _tokenise(prompt)
    prompt_tokens = set(prompt_token_list)
    expanded = _expand_tokens(prompt_token_list)  # [(token, weight)] incl. synonyms
    expanded_set = {t for t, _ in expanded}
    prompt_bigrams = {
        f"{prompt_token_list[i]} {prompt_token_list[i + 1]}"
        for i in range(len(prompt_token_list) - 1)
    }
    prompt_lower = prompt.lower()

    suppressed = set(session_state.get("suppressed", []))
    recent = set(session_state.get("recent", []))

    # Pre-compute cap_id → bigrams it owns (for O(1) per-candidate lookup)
    cap_bigrams_map: dict = {}
    for bg, ids in bigram_index.items():
        for cid in ids:
            cap_bigrams_map.setdefault(cid, set()).add(bg)

    # Use expanded token set (includes synonyms) to maximise candidate recall
    candidate_ids = set()
    for token in expanded_set:
        for cap_id in term_index.get(token, []):
            candidate_ids.add(cap_id)
    for bigram in prompt_bigrams:
        for cap_id in bigram_index.get(bigram, []):
            candidate_ids.add(cap_id)

    # Normalisation denominator — computed once (invariant across candidates)
    prompt_token_weight = sum(idf_index.get(t, DEFAULT_IDF) for t in prompt_tokens)
    prompt_token_weight = max(prompt_token_weight, DEFAULT_IDF)

    results = []
    for cap_id in candidate_ids:
        if cap_id in suppressed:
            continue

        cap = capabilities.get(cap_id)
        if not cap:
            continue
        if not matches_profile(cap):
            continue

        # --- Term score (IDF-weighted, synonym-expanded, field-weighted) ---
        token_fields = cap.get("token_fields")
        if token_fields:
            # Build per-token max field weight, restricted to tokens that are
            # indexed for this specific capability (i.e. in term_index[tok]).
            # This prevents when_short / name tokens not in triggers/one_liner
            # from borrowing a non-zero IDF calibrated against other capabilities.
            token_fw: dict = {}
            for field, fw in FIELD_WEIGHTS.items():
                for tok in token_fields.get(field, []):
                    if cap_id in term_index.get(tok, []) and fw > token_fw.get(tok, 0.0):
                        token_fw[tok] = fw
            if not token_fw:
                continue
            matched_w = [(t, w) for t, w in expanded if t in token_fw]
            term_score = sum(
                idf_index.get(t, DEFAULT_IDF) * w * token_fw[t]
                for t, w in matched_w
            )
        else:
            # Fallback: trigger-only scoring for older index without token_fields
            trigger_tokens = set(_tokenise(" ".join(cap.get("triggers", []))))
            if not trigger_tokens:
                continue
            matched_w = [(t, w) for t, w in expanded if t in trigger_tokens]
            term_score = sum(idf_index.get(t, DEFAULT_IDF) * w for t, w in matched_w)

        # --- Bigram score ---
        bigram_matches = prompt_bigrams & cap_bigrams_map.get(cap_id, set())
        bigram_score = sum(idf_index.get(bg, DEFAULT_IDF) for bg in bigram_matches)

        # --- Signal bonus ---
        signal_bonus = 0.0
        signals = cap.get("signals", {})
        cli_tools = signals.get("cli", [])
        for tool in cli_tools:
            if tool and tool.lower() in prompt_lower:
                signal_bonus += SIGNAL_BONUS
                break

        files_read = signals.get("filesRead", [])
        for pattern in files_read:
            # Extract extension root (e.g. "**/*.java" -> ".java")
            ext = os.path.splitext(pattern)[1]
            if ext and ext in prompt_lower:
                signal_bonus += SIGNAL_BONUS
                break

        # Cap signal bonus at SIGNAL_BONUS (one bonus only per category above)
        # (already limited by `break` in each loop)

        # --- Minimum match guard ---
        # Require at least 2 token matches, unless a strong contextual signal exists:
        # a CLI/file signal or a bigram match (which already implies 2 consecutive tokens).
        min_matches = 1 if (signal_bonus > 0 or bigram_matches) else 2
        if len(matched_w) < min_matches:
            continue

        # --- Negative penalty ---
        negatives = cap.get("negatives", [])
        neg_hit = any(neg.lower() in prompt_lower for neg in negatives if neg)
        negative_penalty = NEGATIVE_PENALTY if neg_hit else 0.0

        # --- Recency prior ---
        recency = RECENCY_PRIOR if cap_id in recent else 0.0

        # --- Raw score ---
        raw_score = term_score + bigram_score + signal_bonus + recency - negative_penalty

        score = raw_score / prompt_token_weight

        if score > SCORE_THRESHOLD:
            # Build chain hint from graph precedes edges (T2-C)
            chain_str = ""
            if graph_chains:
                chain_str = _build_chain_str(cap_id, graph_chains, capabilities)
            requires_str = ""
            if not chain_str and backward_map.get(cap_id):
                requires_str = _build_predecessor_str(cap_id, graph_chains, backward_map, capabilities)
            results.append({
                "capability_id": cap_id,
                "score": round(score, 4),
                "command": cap.get("command", ""),
                "one_liner": cap.get("one_liner", ""),
                "install_info": cap.get("install_info", ""),
                "chain": chain_str,
                "requires": requires_str,
                "when_to_use_short": cap.get("when_to_use_short", ""),
                "not_for": cap.get("not_for", ""),
                "domain": cap.get("domain", ""),
            })

    # --- Fuzzy fallback (only when zero candidates above threshold) ---
    if not results and term_index:
        all_trigger_terms = set(term_index.keys())
        fuzzy_tokens = fuzzy_expand_tokens(prompt_token_list, all_trigger_terms)
        if fuzzy_tokens:
            fuzzy_candidate_ids: set = set()
            for ft in fuzzy_tokens:
                for cid in term_index.get(ft, []):
                    fuzzy_candidate_ids.add(cid)
            for cap_id in fuzzy_candidate_ids:
                if cap_id in suppressed:
                    continue
                cap = capabilities.get(cap_id)
                if not cap:
                    continue
                if not matches_profile(cap):
                    continue
                _token_fields = cap.get("token_fields")
                if _token_fields:
                    _token_fw: dict = {}
                    for _f, _fw in FIELD_WEIGHTS.items():
                        for _tok in _token_fields.get(_f, []):
                            if cap_id in term_index.get(_tok, []) and _fw > _token_fw.get(_tok, 0.0):
                                _token_fw[_tok] = _fw
                    if not _token_fw:
                        continue
                    matched_w = [(t, 0.6 * _token_fw[t]) for t in fuzzy_tokens if t in _token_fw]
                    term_score = sum(idf_index.get(t, DEFAULT_IDF) * w for t, w in matched_w)
                else:
                    trigger_tokens = set(_tokenise(" ".join(cap.get("triggers", []))))
                    if not trigger_tokens:
                        continue
                    matched_w = [(t, 0.6) for t in fuzzy_tokens if t in trigger_tokens]
                    term_score = sum(idf_index.get(t, DEFAULT_IDF) * w for t, w in matched_w)
                if not matched_w:
                    continue
                bigram_score = sum(
                    idf_index.get(bg, DEFAULT_IDF)
                    for bg in (prompt_bigrams & cap_bigrams_map.get(cap_id, set()))
                )
                signal_bonus = 0.0
                for tool in cap.get("signals", {}).get("cli", []):
                    if tool and tool.lower() in prompt_lower:
                        signal_bonus += SIGNAL_BONUS
                        break
                raw_score = term_score + bigram_score + signal_bonus + (
                    RECENCY_PRIOR if cap_id in recent else 0.0
                )
                score = raw_score / prompt_token_weight
                if score > SCORE_THRESHOLD:
                    chain_str = ""
                    if graph_chains:
                        chain_str = _build_chain_str(cap_id, graph_chains, capabilities)
                    requires_str = ""
                    if not chain_str and backward_map.get(cap_id):
                        requires_str = _build_predecessor_str(cap_id, graph_chains, backward_map, capabilities)
                    results.append({
                        "capability_id": cap_id,
                        "score": round(score, 4),
                        "command": cap.get("command", ""),
                        "one_liner": cap.get("one_liner", ""),
                        "install_info": cap.get("install_info", ""),
                        "chain": chain_str,
                        "requires": requires_str,
                        "when_to_use_short": cap.get("when_to_use_short", ""),
                        "not_for": cap.get("not_for", ""),
                        "domain": cap.get("domain", ""),
                    })

    # Stable tie-breaking by capability_id ensures deterministic ordering
    # regardless of Python hash-seed-based set iteration.
    results.sort(key=lambda x: (-x["score"], x["capability_id"]))
    results = _apply_diversity_penalty(results)
    return results[:TOP_N]


def main() -> None:
    # Ensure UTF-8 for stdin/stdout on Windows (default encoding is cp1252 there)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    plugin_root = os.environ.get(
        "CLAUDE_PLUGIN_ROOT",
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    # Parse stdin
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except Exception:
        json.dump({"match": False, "candidates": [], "error": "parse_error"}, sys.stdout)
        sys.stdout.flush()
        sys.exit(0)

    prompt = payload.get("prompt", "")
    session_state = payload.get("session_state", {})
    if not isinstance(session_state, dict):
        session_state = {}

    # Load index and graph chains — both fail open
    index = _load_index(plugin_root)
    if not index or not index.get("capabilities"):
        json.dump(_empty_response(), sys.stdout)
        sys.stdout.flush()
        sys.exit(0)

    graph_chains = _load_graph_chains(plugin_root)
    candidates = score_candidates(prompt, session_state, index, graph_chains)

    result = {
        "match": len(candidates) > 0,
        "candidates": candidates,
    }
    json.dump(result, sys.stdout)
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
