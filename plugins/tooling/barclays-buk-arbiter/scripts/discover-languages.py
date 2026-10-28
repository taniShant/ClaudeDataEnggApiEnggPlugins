#!/usr/bin/env python3
"""Batch language discovery CLI tool.

Discovers programming languages and build systems in a repository.
Can be invoked standalone or by /arbiter-discover command.
"""

import sys
import json
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.language_detector import detect_languages, detect_build_system

def main():
    parser = argparse.ArgumentParser(
        description="Discover programming languages and frameworks in a repository"
    )
    parser.add_argument("repo_path", nargs="?", default=".", help="Path to repository (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--quick", action="store_true", help="Quick scan (file extensions only, no build system check)")

    args = parser.parse_args()
    repo_path = args.repo_path

    try:
        result = detect_languages(repo_path)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            # Human-readable output
            print("=" * 60)
            print("Language & Framework Discovery Report")
            print("=" * 60)
            print(f"\n📁 Repository: {result['repository_path']}")
            print(f"📊 Total files: {result['total_files']}")

            if not result['languages_detected']:
                print("\n⚠️  No analyzable languages detected")
                sys.exit(0)

            print("\n🔍 Languages detected:")
            for lang in result['languages_detected']:
                bar_length = int(lang['percentage'] / 2)
                bar = "█" * bar_length + "░" * (50 - bar_length)
                print(f"  {lang['language']:12} {bar} {lang['file_count']:6} files ({lang['percentage']:5.1f}%)")

            if result['build_system']:
                print(f"\n🔨 Build system: {result['build_system']}")

            recommendation = result['recommendation']
            print(f"\n✨ Recommendation:")
            print(f"   Primary language: {recommendation['primary_language']}")
            print(f"   Analyzer tier: {recommendation['analyzer_tier']}")
            print(f"   Confidence: {recommendation['confidence']}")

            print("\n💡 Next step: /arbiter-analyze to build call graph")
            print("=" * 60)

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
