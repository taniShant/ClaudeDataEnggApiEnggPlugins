---
user-invocable: false
description: "iOS framework detection rules — UIKit, SwiftUI, Combine, Core Data, Codable, React Native"
---

# Skill: iOS Framework Detection

## Source Attribution

Rules derived from Apple framework documentation, UIKit/SwiftUI lifecycle contracts, and Barclays iOS app patterns (React Native bridge, coordinator navigation).

## Agent Self-Check

- [ ] UIKit lifecycle methods always protected (viewDidLoad, etc.)
- [ ] @IB* annotations cause appropriate deductions
- [ ] SwiftUI property wrappers handled (not just @State but all @-prefixed)
- [ ] Codable/NSCoding conformance protects init(from:)/encode(to:)
- [ ] Core Data @NSManaged properties protected
- [ ] React Native bridge patterns auto-KEEP
- [ ] Protocol data source/delegate methods protected

---

## Framework Rules Summary (Arbiter 0-4 Scale)

### Always-Keep Methods (Auto-KEEP, score = 0)

These methods are called by iOS frameworks at runtime. Removing them crashes the app:

**UIViewController Lifecycle:**
- `viewDidLoad`, `viewWillAppear`, `viewDidAppear`
- `viewWillDisappear`, `viewDidDisappear`
- `viewWillLayoutSubviews`, `viewDidLayoutSubviews`
- `loadView`, `didReceiveMemoryWarning`

**UITableView/UICollectionView Data Source:**
- `tableView(_:numberOfRowsInSection:)`, `tableView(_:cellForRowAt:)`
- `collectionView(_:numberOfItemsInSection:)`, `collectionView(_:cellForItemAt:)`

**UIApplicationDelegate:**
- `application(_:didFinishLaunchingWithOptions:)`
- `applicationWillResignActive`, `applicationDidEnterBackground`

**UISceneDelegate:**
- `scene(_:willConnectTo:options:)`, `sceneDidDisconnect`

**Codable/NSCoding:**
- `init(from:)`, `encode(to:)`, `init(coder:)`, `encode(with:)`

**SwiftUI:**
- `body`, `makeBody`, `makeCoordinator`
- `updateUIViewController`, `makeUIViewController`

**Combine:**
- `receive(subscription:)`, `receive(_:)`, `receive(completion:)`

---

### Annotation Deduction Table

| Annotation | Deduction | Impact | Reason |
|-----------|-----------|--------|--------|
| `@main` | -4.0 | KEEP | Application entry point |
| `@UIApplicationMain` | -4.0 | KEEP | Application entry point |
| `@IBAction` | -2.0 | → LIKELY | Interface Builder action |
| `@IBOutlet` | -2.0 | → LIKELY | Interface Builder outlet |
| `@NSManaged` | -2.0 | → LIKELY | Core Data managed |
| `@objc` | -1.5 | → LIKELY | ObjC runtime exposed |
| `@objcMembers` | -1.5 | → LIKELY | All members ObjC exposed |
| `@IBDesignable` | -1.0 | Minor | IB designable view |
| `@IBInspectable` | -1.0 | Minor | IB inspectable property |
| `@Published` | -0.7 | Minor | Combine publisher |
| `@State` | -0.7 | Minor | SwiftUI state |
| `@Binding` | -0.7 | Minor | SwiftUI binding |
| `@ObservedObject` | -0.7 | Minor | SwiftUI observed |
| `@StateObject` | -0.7 | Minor | SwiftUI state object |
| `@EnvironmentObject` | -0.7 | Minor | SwiftUI environment |
| `@Environment` | -0.5 | Minor | SwiftUI environment value |
| `@MainActor` | -0.5 | Minor | Main thread isolated |

---

### Superclass Deduction Table

| Superclass | Deduction | Reason |
|-----------|-----------|--------|
| `UIApplicationDelegate` | -4.0 (KEEP) | App delegate |
| `UINavigationController` | -0.8 | Navigation controller |
| `UITabBarController` | -0.8 | Tab bar controller |
| `UIViewController` | -0.7 | View controller |
| `UITableViewController` | -0.7 | Table view controller |
| `UICollectionViewController` | -0.7 | Collection view controller |
| `UITableViewCell` | -0.7 | Table view cell |
| `UICollectionViewCell` | -0.7 | Collection view cell |
| `ObservableObject` | -0.7 | Combine observable |
| `UIView` | -0.5 | View subclass |
| `UIControl` | -0.5 | Control subclass |
| `UIResponder` | -0.5 | Responder chain |
| `NSManagedObject` | -1.5 | Core Data entity |
| `NSObject` | -0.3 | ObjC interop |

---

### Protocol Conformance Deduction Table

| Protocol | Deduction | Reason |
|---------|-----------|--------|
| `App` | -4.0 (KEEP) | SwiftUI app entry |
| `UITableViewDataSource` | -1.0 | Table data source |
| `UICollectionViewDataSource` | -1.0 | Collection data source |
| `Codable` | -1.0 | Serialization |
| `NSCoding` | -1.0 | NSCoding serialization |
| `View` | -1.0 | SwiftUI view |
| `UITableViewDelegate` | -0.8 | Table delegate |
| `UICollectionViewDelegate` | -0.8 | Collection delegate |
| `Decodable` | -0.8 | Deserialization |
| `Encodable` | -0.8 | Serialization |
| `UINavigationControllerDelegate` | -0.7 | Navigation delegate |
| `UIScrollViewDelegate` | -0.7 | Scroll delegate |
| `UITextFieldDelegate` | -0.7 | Text field delegate |
| `UISearchBarDelegate` | -0.7 | Search delegate |
| `UICollectionViewDelegateFlowLayout` | -0.7 | Layout delegate |
| `Hashable` | -0.3 | Collection usage |
| `Equatable` | -0.2 | Equality |
| `CustomStringConvertible` | -0.2 | Debug description |
| `PreviewProvider` | 0.0 | Dev-only (safe to remove) |

---

### React Native Bridge (Auto-KEEP)

Any class or method containing these patterns is auto-KEEP:
- `RCT_EXPORT_MODULE`
- `RCT_EXPORT_METHOD`
- `RCT_EXTERN_MODULE`
- `RCT_EXTERN_METHOD`
- `RCTBridgeModule` conformance
- `RCTEventEmitter` subclass

---

### Resource References (Storyboard/XIB)

| Reference Type | Deduction | Notes |
|---------------|-----------|-------|
| `customClass` in storyboard | -2.5 | → UNCERTAIN. Class instantiated by IB at runtime |
| IBOutlet connection | -2.0 | Property connected in IB |
| IBAction connection | -2.0 | Method connected in IB |
| Segue destination | -1.5 | Implicitly instantiated |

---

### Dynamic Dispatch

| Pattern | Deduction | Notes |
|---------|-----------|-------|
| NSClassFromString target | -2.0 | Class instantiated by string |
| NSSelectorFromString target | -1.5 | Method called by selector string |
| performSelector target | -1.5 | ObjC message dispatch |
| KVC forKey target | -1.5 | Property accessed by string |
| Constructed selector prefix match | -1.0 | Heuristic match |
