# Arbiter Plugin Python Implementation
# Dead code detection and removal for Java projects
# Token-optimized: Deterministic logic only, no LLM reasoning

__version__ = "1.0.0"
__author__ = "Preetha Ramaswamy"

from .language_detector import detect_languages, detect_build_system
from .call_graph_analyzer import build_call_graph
from .deadcode_finder import find_dead_code_candidates
from .removal_executor import execute_removal
from .validator import validate_removal

__all__ = [
    "detect_languages",
    "detect_build_system",
    "build_call_graph",
    "find_dead_code_candidates",
    "execute_removal",
    "validate_removal",
]
