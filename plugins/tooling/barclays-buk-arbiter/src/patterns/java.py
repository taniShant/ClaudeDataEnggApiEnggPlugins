#!/usr/bin/env python3
"""Java-specific patterns for framework detection and analysis."""

import re
from typing import List, Dict, Any

SPRING_PATTERNS = {
    "entry_point": [
        r"@SpringBootApplication",
        r"@RestController",
        r"@Service",
        r"@Component",
        r"@Repository",
    ],
    "scheduled": [
        r"@Scheduled",
        r"@Async",
        r"@EventListener",
    ],
    "http": [
        r"@GetMapping",
        r"@PostMapping",
        r"@PutMapping",
        r"@DeleteMapping",
    ]
}

def detect_java_patterns(code: str) -> Dict[str, List[str]]:
    """Detect Spring and other Java framework patterns."""
    detected = {}
    for category, patterns in SPRING_PATTERNS.items():
        detected[category] = []
        for pattern in patterns:
            if re.search(pattern, code):
                detected[category].append(pattern)
    return detected

def extract_entry_points(code: str) -> List[str]:
    """Extract method signatures that are entry points."""
    entry_points = []
    # TODO: Implement entry point extraction
    return entry_points
