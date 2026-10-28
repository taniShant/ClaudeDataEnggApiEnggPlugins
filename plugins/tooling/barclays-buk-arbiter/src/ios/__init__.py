# Arbiter iOS/Swift Dead Code Analysis
# Extension for Swift and Objective-C dead code detection and removal

__version__ = "1.0.0"

from .ios_detector import iOSDetector, iOSProjectMetadata
from .ios_confidence_engine import IOSConfidenceEngine
from .ios_framework_rules import (
    ALWAYS_KEEP_METHODS,
    FRAMEWORK_MANAGED_ANNOTATIONS,
    FRAMEWORK_SUPERCLASSES,
    FRAMEWORK_PROTOCOLS,
    REACT_NATIVE_PATTERNS,
)
from .ios_dynamic_dispatch_scanner import DynamicDispatchScanner, scan_dynamic_dispatch
from .ios_resource_scanner import scan_all_resources
from .ios_call_graph_analyzer import build_ios_call_graph
from .ios_deadcode_finder import find_ios_dead_code_candidates
from .ios_removal_executor import execute_ios_removal
from .ios_planner import IOSRemovalPlanner, plan_ios_removals

__all__ = [
    "iOSDetector",
    "iOSProjectMetadata",
    "IOSConfidenceEngine",
    "DynamicDispatchScanner",
    "scan_dynamic_dispatch",
    "scan_all_resources",
    "build_ios_call_graph",
    "find_ios_dead_code_candidates",
    "execute_ios_removal",
    "IOSRemovalPlanner",
    "plan_ios_removals",
]
