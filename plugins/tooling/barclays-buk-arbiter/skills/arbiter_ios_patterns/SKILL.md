---
user-invocable: false
description: "iOS/Swift/ObjC code patterns that create hidden usage invisible to static analysis"
---

# Skill: iOS Patterns & Hidden Usage

## Source Attribution

Patterns derived from UIKit, SwiftUI, Combine, Core Data frameworks and Barclays iOS app architecture (coordinator pattern, React Native bridge).

## Agent Self-Check

- [ ] Protocol conformance usage detected (DI containers, type-erased collections)
- [ ] Property wrappers recognized as usage (@State, @Published, @Environment)
- [ ] Storyboard/XIB references checked (customClass is invisible to source analysis)
- [ ] Dynamic dispatch patterns handled (NSSelectorFromString, NSClassFromString)
- [ ] Coordinator pattern recognized (lazy instantiation = usage)
- [ ] Override methods treated as framework-called

---

## Quick-Reference: Hidden Usage Patterns

### Protocol Conformances (⚠️ Hidden Usage)

Types registered in dependency injection containers are "used" even if no direct call exists:
```swift
// This class looks unused but is resolved via DI at runtime
class PaymentService: PaymentServiceProtocol {
    func processPayment() { ... }
}
// Registered in container: container.register(PaymentServiceProtocol.self) { PaymentService() }
```
**Rule:** If a type conforms to a protocol, check for container registration patterns.

### Property Wrappers (⚠️ Hidden Usage)

Every `@TypeName` annotation is a type usage:
```swift
@Published var balance: Double  // "Published" type is used
@State var isLoading: Bool      // "State" type is used
@FetchRequest var items: ...    // "FetchRequest" type is used
```
**Rule:** Property wrapper types are always in use.

### Result Builders (⚠️ Compiler-Invoked)

```swift
@resultBuilder struct ViewBuilder { ... }  // Compiler calls buildBlock, buildIf, etc.
```
**Rule:** Result builder methods are called by the compiler, not user code.

### Key Paths (⚠️ Invisible References)

```swift
let agePath = \Person.age  // "age" property is used but won't appear in call graph
```
**Rule:** Check for key path references to properties.

### Selector-Based Dispatch (⚠️ String References)

```swift
NotificationCenter.default.addObserver(self, selector: #selector(handleUpdate), ...)
Timer.scheduledTimer(timeInterval: 1.0, target: self, selector: #selector(tick), ...)
```
**Rule:** Methods referenced by #selector or NSSelectorFromString are in use.

---

## Objective-C Patterns

### Dynamic Dispatch (⚠️ Runtime Resolution)

```objc
SEL selector = NSSelectorFromString(@"handleAction");
[target performSelector:selector];

Class cls = NSClassFromString(@"PaymentViewController");
[[cls alloc] init];
```
**Rule:** Any name passed to NSSelectorFromString/NSClassFromString is protected.

### KVO/KVC (⚠️ String-Based Property Access)

```objc
[object addObserver:self forKeyPath:@"balance" options:0 context:nil];
[object setValue:@100 forKey:@"amount"];
```
**Rule:** Properties referenced via KVO/KVC strings are in use.

### Categories (⚠️ Global Extension)

```objc
@interface NSString (BUKFormatting)
- (NSString *)buk_formattedAmount;
@end
```
**Rule:** Category methods are callable from anywhere — treat as public API.

---

## Coordinator Pattern (Barclays iOS)

Types instantiated inside lazy properties or factory methods are "used":
```swift
class AppCoordinator {
    lazy var paymentCoordinator = PaymentCoordinator()  // PaymentCoordinator is used
    
    func start() {
        // PaymentCoordinator looks unreferenced but is lazily instantiated
    }
}
```
**Rule:** Check lazy properties and factory methods for type instantiation.

---

## Storyboard Instantiation (⚠️ String-Based)

```swift
let vc = storyboard.instantiateViewController(withIdentifier: "PaymentVC")
```
**Rule:** String literals near `instantiateViewController` reference class names.

---

## Safe Removal Patterns by Entity Type

### Classes/Structs (confidence depends on signals)

| Signal | Confidence | Action |
|--------|-----------|--------|
| Private + no usage | 4.0 (SAFE) | Delete file |
| Internal + no usage + no storyboard ref | 3.5 (SAFE) | Delete file |
| Public + no usage | 3.0 (SAFE boundary) | Review first |
| Storyboard customClass | 1.5 (UNCERTAIN) | Manual review |
| Framework superclass + no usage | 2.5 (LIKELY) | Review lifecycle |

### Methods

| Signal | Confidence | Action |
|--------|-----------|--------|
| Private + no call | 4.0 (SAFE) | Comment out |
| Override (no super call) | 2.0 (LIKELY) | May be framework-called |
| @objc + no direct call | 2.5 (LIKELY) | May be selector-dispatched |
| #selector target | 0 (KEEP) | Selector usage detected |

### Properties

| Signal | Confidence | Action |
|--------|-----------|--------|
| Private + never read/written | 4.0 (SAFE) | Remove |
| @IBOutlet + no storyboard connection | 3.0 (SAFE) | Remove |
| KVC target | 0 (KEEP) | String-based access |

---

## Anti-Patterns: High False-Positive Risk

1. **Dynamic dispatch heavy code** — ObjC-heavy modules, data-driven navigation
2. **Serialization** — Codable/NSCoding properties accessed only during encode/decode
3. **Core Data entities** — @NSManaged properties accessed by framework, not code
4. **React Native bridge** — RCT_EXPORT_MODULE classes called from JavaScript
5. **Widget extensions** — Entry points configured in Info.plist, not code
