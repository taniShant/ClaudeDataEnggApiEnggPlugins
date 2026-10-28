#!/usr/bin/env python3
"""Language detection for repositories.

Detects programming languages, build systems, and frameworks.
Recommends appropriate analyzer tier for dead code analysis.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

def detect_languages(repo_path: str = ".") -> Dict[str, Any]:
    """
    Detect programming languages in repository by scanning file extensions.

    Args:
        repo_path: Path to repository (default: current directory)

    Returns:
        Dictionary with detected languages, file counts, percentages, build systems
    """
    repo_path = Path(repo_path)

    # File extension patterns
    language_patterns = {
        "java": ["*.java"],
        "python": ["*.py"],
        "javascript": ["*.js", "*.jsx"],
        "typescript": ["*.ts", "*.tsx"],
        "kotlin": ["*.kt"],
        "go": ["*.go"],
        "ruby": ["*.rb"],
        "php": ["*.php"],
        "csharp": ["*.cs"],
        "cpp": ["*.cpp", "*.cc", "*.c++"],
        "c": ["*.c"],
        "header": ["*.h", "*.hpp"],
    }

    file_counts = {}
    total_files = 0

    for language, patterns in language_patterns.items():
        count = 0
        for pattern in patterns:
            try:
                count += len(list(repo_path.glob(f"**/{pattern}")))
            except Exception:
                pass
        if count > 0:
            file_counts[language] = count
            total_files += count

    # Calculate percentages
    languages_detected = []
    for language, count in sorted(file_counts.items(), key=lambda x: -x[1]):
        percentage = (count / total_files * 100) if total_files > 0 else 0
        if percentage >= 1.0:  # Only include >=1% (include languages at threshold)
            languages_detected.append({
                "language": language,
                "file_count": count,
                "percentage": round(percentage, 2),
            })

    build_system = detect_build_system(repo_path)

    return {
        "detection_timestamp": datetime.now().isoformat(),
        "repository_path": str(repo_path),
        "total_files": total_files,
        "languages_detected": languages_detected,
        "build_system": build_system,
        "recommendation": {
            "primary_language": languages_detected[0]["language"] if languages_detected else None,
            "analyzer_tier": "compiled" if build_system else "grep",
            "confidence": "high" if build_system else "medium",
        }
    }

def detect_build_system(repo_path: Path) -> str:
    """
    Detect build system (Gradle, Maven, etc.) by looking for build files.
    """
    build_indicators = {
        "gradle": ["build.gradle", "build.gradle.kts", "settings.gradle"],
        "maven": ["pom.xml"],
        "npm": ["package.json"],
        "go": ["go.mod"],
    }

    for build_system, files in build_indicators.items():
        for file in files:
            if (repo_path / file).exists():
                return build_system

    return None

if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    result = detect_languages(repo)
    print(json.dumps(result, indent=2))
