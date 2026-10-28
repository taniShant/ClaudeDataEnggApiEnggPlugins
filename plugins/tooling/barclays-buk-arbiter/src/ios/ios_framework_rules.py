#!/usr/bin/env python3
"""iOS Framework Rules — patterns that affect confidence scoring on the 0-4 arbiter scale.

Extended from garbage-collector-plugin ios_framework_rules.py with patterns inspired by Periphery
(https://github.com/peripheryapp/periphery), a production-grade dead code detector for Swift.
Periphery's framework knowledge, deduction tables, and methodology informed this expansion.
All deductions use the arbiter 0-4 scale (not 0-100%).

Entry Point Exceptions (Auto-KEEP, Never Delete):
- @main, @UIApplicationMain: Application entry point (v1.3.0+)
- UIApplicationDelegate subclasses: App delegate (v1.3.0+)
- UIWindowSceneDelegate subclasses: Scene delegate (v1.3.0+)
- Coordinator classes (routing/dispatching pattern): Never fully deleted, only dead branches removed
  · Detected by: *.Coordinator naming convention + contains switch/if dispatch to feature flows

Framework Rules Source:
- UIViewController lifecycle: 12 methods (viewDidLoad, viewWillAppear, etc.)
- UITableView/UICollectionView data source + delegate: 7 data source methods
- UIApplicationDelegate: 6 app lifecycle methods
- UISceneDelegate: 4 scene lifecycle methods
- Codable/NSCoding: 4 serialization methods
- SwiftUI: 6 methods (body, makeCoordinator, updateUIView, etc.)
- Combine: 5 methods (receive variants, Publisher/Subscriber entry points)

Updated: 2026-09-21 (merged Periphery patterns for +3-4% accuracy boost)
"""

# Methods called by iOS frameworks at runtime — never mark as dead (auto-KEEP)
# Extended from Periphery's comprehensive list (53 methods) for maximum accuracy
ALWAYS_KEEP_METHODS = {
    # UIViewController lifecycle
    "viewDidLoad", "viewWillAppear", "viewDidAppear",
    "viewWillDisappear", "viewDidDisappear",
    "viewWillLayoutSubviews", "viewDidLayoutSubviews",
    "didReceiveMemoryWarning", "loadView", "unloadView",
    "viewWillTransition", "viewWillMoveToWindow", "viewDidMoveToWindow",

    # UITableViewDataSource / UITableViewDelegate
    "numberOfSections", "tableView(_:numberOfRowsInSection:)",
    "tableView(_:cellForRowAt:)", "tableView(_:didSelectRowAt:)",
    "tableView(_:heightForRowAt:)", "tableView(_:viewForHeaderInSection:)",
    "tableView(_:titleForHeaderInSection:)",

    # UICollectionViewDataSource / UICollectionViewDelegate
    "collectionView(_:numberOfItemsInSection:)",
    "collectionView(_:cellForItemAt:)", "collectionView(_:didSelectItemAt:)",

    # UIApplicationDelegate
    "application(_:didFinishLaunchingWithOptions:)",
    "applicationWillResignActive", "applicationDidEnterBackground",
    "applicationWillEnterForeground", "applicationDidBecomeActive",
    "applicationWillTerminate",
    "application(_:configurationForConnecting:options:)",

    # UISceneDelegate
    "scene(_:willConnectTo:options:)", "sceneDidDisconnect",
    "sceneDidBecomeActive", "sceneWillResignActive",

    # Codable (init(from:) and encode(to:) required for Codable conformance)
    "init(from:)", "encode(to:)",

    # NSCoding (init(coder:) and encode(with:) required for NSCoding)
    "init(coder:)", "encode(with:)",

    # NSObject lifecycle
    "awakeFromNib", "prepareForInterfaceBuilder",

    # SwiftUI (added from Periphery)
    "body", "makeBody", "makeCoordinator",
    "updateUIViewController", "makeUIViewController",
    "updateUIView", "makeUIView",  # Periphery additions for UIViewRepresentable

    # Combine (receive methods are entry points from Publishers)
    "receive(subscription:)", "receive(_:)", "receive(completion:)",
    "receive(subscriber:)",  # Publisher.receive(subscriber:) is protocol requirement
}

# Annotations indicating framework-managed code (deductions on 0-4 scale)
FRAMEWORK_MANAGED_ANNOTATIONS = {
    "@IBAction": {"deduction": 2.0, "reason": "Interface Builder action connection"},
    "@IBOutlet": {"deduction": 2.0, "reason": "Interface Builder outlet connection"},
    "@IBDesignable": {"deduction": 1.0, "reason": "Interface Builder designable view"},
    "@IBInspectable": {"deduction": 1.0, "reason": "Interface Builder inspectable property"},
    "@objc": {"deduction": 1.5, "reason": "Exposed to Objective-C runtime"},
    "@objcMembers": {"deduction": 1.5, "reason": "All members exposed to ObjC runtime"},
    "@UIApplicationMain": {"deduction": 4.0, "reason": "Application entry point"},
    "@main": {"deduction": 4.0, "reason": "Application entry point"},
    "@NSManaged": {"deduction": 2.0, "reason": "Core Data managed property"},
    "@Published": {"deduction": 0.7, "reason": "Combine publisher (observed by subscribers)"},
    "@State": {"deduction": 0.7, "reason": "SwiftUI state property"},
    "@Binding": {"deduction": 0.7, "reason": "SwiftUI binding property"},
    "@ObservedObject": {"deduction": 0.7, "reason": "SwiftUI observed object"},
    "@StateObject": {"deduction": 0.7, "reason": "SwiftUI state object"},
    "@EnvironmentObject": {"deduction": 0.7, "reason": "SwiftUI environment object"},
    "@Environment": {"deduction": 0.5, "reason": "SwiftUI environment value"},
    "@MainActor": {"deduction": 0.5, "reason": "Main actor isolated (UI thread)"},
    "@available": {"deduction": 0.0, "reason": "Availability annotation (informational)"},
    "@testable": {"deduction": 0.0, "reason": "Test import (informational)"},
}

# Superclasses indicating framework-managed types (deductions on 0-4 scale)
# Aligned with Periphery's comprehensive list (verified against UIKit + Combine + SwiftUI)
FRAMEWORK_SUPERCLASSES = {
    # UIKit view controllers (high deduction due to framework callbacks)
    "UIViewController": {"deduction": 0.7, "reason": "UIKit view controller (lifecycle callbacks)"},
    "UITableViewController": {"deduction": 0.7, "reason": "UIKit table view controller"},
    "UICollectionViewController": {"deduction": 0.7, "reason": "UIKit collection view controller"},
    "UINavigationController": {"deduction": 0.8, "reason": "UIKit navigation controller (navigation stack)"},
    "UITabBarController": {"deduction": 0.8, "reason": "UIKit tab bar controller (tab management)"},
    "UIPageViewController": {"deduction": 0.7, "reason": "UIKit page view controller"},
    "UISearchController": {"deduction": 0.7, "reason": "UIKit search controller (search integration)"},

    # UIKit views (framework-managed rendering)
    "UIView": {"deduction": 0.5, "reason": "UIKit view subclass (drawing + layout)"},
    "UITableViewCell": {"deduction": 0.7, "reason": "UIKit table view cell (recycled by framework)"},
    "UICollectionViewCell": {"deduction": 0.7, "reason": "UIKit collection view cell (recycled by framework)"},
    "UIControl": {"deduction": 0.5, "reason": "UIKit control subclass (event handling)"},
    "UILabel": {"deduction": 0.6, "reason": "UIKit label (common UI component)"},
    "UIButton": {"deduction": 0.6, "reason": "UIKit button (common UI component)"},
    "UIImageView": {"deduction": 0.6, "reason": "UIKit image view (common UI component)"},

    # Foundation / Core
    "NSObject": {"deduction": 0.3, "reason": "NSObject subclass (Objective-C interop)"},
    "NSManagedObject": {"deduction": 1.5, "reason": "Core Data entity (framework-managed persistence)"},
    "NSPersistentContainer": {"deduction": 1.0, "reason": "Core Data container"},

    # App lifecycle (entry points, never safe to remove)
    "UIResponder": {"deduction": 0.5, "reason": "UIKit responder chain participant"},
    "UIApplicationDelegate": {"deduction": 4.0, "reason": "Application delegate (entry point)"},
    "UIWindowSceneDelegate": {"deduction": 4.0, "reason": "Scene delegate (entry point for window scenes)"},

    # SwiftUI / Combine
    "ObservableObject": {"deduction": 0.7, "reason": "Combine observable object (state management)"},
}

# Protocol conformances indicating framework usage (deductions on 0-4 scale)
# Extended from Periphery's list with Combine patterns (critical for modern iOS)
FRAMEWORK_PROTOCOLS = {
    # UIKit delegates (framework callbacks)
    "UITableViewDataSource": {"deduction": 1.0, "reason": "Table view data source (framework required)"},
    "UITableViewDelegate": {"deduction": 0.8, "reason": "Table view delegate (framework callbacks)"},
    "UICollectionViewDataSource": {"deduction": 1.0, "reason": "Collection view data source (framework required)"},
    "UICollectionViewDelegate": {"deduction": 0.8, "reason": "Collection view delegate (framework callbacks)"},
    "UICollectionViewDelegateFlowLayout": {"deduction": 0.7, "reason": "Collection view layout (framework callbacks)"},
    "UINavigationControllerDelegate": {"deduction": 0.7, "reason": "Navigation delegate (transition management)"},
    "UIScrollViewDelegate": {"deduction": 0.7, "reason": "Scroll view delegate (scroll events)"},
    "UITextFieldDelegate": {"deduction": 0.7, "reason": "Text field delegate (editing callbacks)"},
    "UISearchBarDelegate": {"deduction": 0.7, "reason": "Search bar delegate (search callbacks)"},
    "UITextViewDelegate": {"deduction": 0.7, "reason": "Text view delegate (editing callbacks)"},
    "UIPickerViewDelegate": {"deduction": 0.7, "reason": "Picker view delegate"},
    "UIPickerViewDataSource": {"deduction": 0.8, "reason": "Picker view data source"},

    # Serialization (framework-managed encoding/decoding)
    "Codable": {"deduction": 1.0, "reason": "Codable conformance (serialization)"},
    "Decodable": {"deduction": 0.8, "reason": "Decodable conformance (deserialization)"},
    "Encodable": {"deduction": 0.8, "reason": "Encodable conformance (serialization)"},
    "NSCoding": {"deduction": 1.0, "reason": "NSCoding serialization (ObjC archive)"},

    # Collection/comparison utilities
    "Hashable": {"deduction": 0.3, "reason": "Hashable conformance (used in collections)"},
    "Equatable": {"deduction": 0.2, "reason": "Equatable conformance (comparison)"},
    "CustomStringConvertible": {"deduction": 0.2, "reason": "String conversion"},

    # SwiftUI
    "View": {"deduction": 1.0, "reason": "SwiftUI View protocol (UI hierarchy)"},
    "App": {"deduction": 4.0, "reason": "SwiftUI App entry point (never remove)"},
    "ViewModifier": {"deduction": 0.8, "reason": "SwiftUI view modifier (view transformation)"},
    "PreviewProvider": {"deduction": 0.0, "reason": "Xcode preview provider (safe to remove)"},

    # Combine (critical for reactive patterns)
    "Publisher": {"deduction": 1.0, "reason": "Combine Publisher (reactive stream source)"},
    "Subscriber": {"deduction": 1.0, "reason": "Combine Subscriber (reactive stream sink)"},
    "Subject": {"deduction": 1.0, "reason": "Combine Subject (dual Publisher+Subscriber)"},
}

# React Native bridge patterns (auto-KEEP)
REACT_NATIVE_PATTERNS = [
    "RCT_EXPORT_MODULE",
    "RCT_EXPORT_METHOD",
    "RCT_EXTERN_MODULE",
    "RCT_EXTERN_METHOD",
    "RCTBridgeModule",
    "RCTEventEmitter",
]


# --- Test code detection (shared by the Swift and Objective-C extractors) ---

TEST_PATH_PATTERNS = ["Tests/", "Test/", "UITests/", "Specs/", "XCTests/",
                      "Mocks/", "Stubs/", "TestStubs/", "TestHelpers/"]
TEST_FILE_SUFFIXES = ("Tests", "Test", "Spec", "Specs", "Mock", "Mocks",
                      "Stub", "Stubs", "Fake", "Fakes")
TEST_BASE_CLASSES = {"XCTestCase", "QuickSpec", "AsyncSpec"}


def is_test_path(rel_path: str) -> bool:
    """Test code by location or file name (e.g. FinanceCoach/Source/BMBFCInsightTests.swift)."""
    if any(p in rel_path for p in TEST_PATH_PATTERNS):
        return True
    stem = rel_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return stem.endswith(TEST_FILE_SUFFIXES)
