---
name: ios
description: BMB SwiftUI + BarclaysBlueprint patterns for the Barclays iOS platform. Covers module structure, ViewModel, DI, Blueprint component map, theme tokens, testing, localisation, accessibility, and security. Load this skill in all ui-engineer-ios agents.
user-invocable: false
owner: BUK PE
review_trigger: BarclaysBlueprint major version bump, iOS architecture review
---

# iOS UI Skill — BMB SwiftUI + BarclaysBlueprint Patterns

> **Source:** barclays/mobile-ios-client (project 119872, branch release/R26.07.01) and blueprint-swift (project 118950)
> **Owner:** BUK PE
> **Review trigger:** BarclaysBlueprint major version bump, iOS architecture review
> **Status:** Reviewed 2026-07-21

This skill encodes the structural patterns used in the Barclays Mobile Banking (BMB) iOS codebase. Every generated file must comply with these patterns. Deviations produce code that will not compile or will be rejected at code review.

---

## Quick Start

```swift
// Typical task: generate one SwiftUI view + ObservableObject ViewModel

// 1. View (Section 4) — @StateObject owns the ViewModel
struct CardDetailsView: View {
    @StateObject private var viewModel: CardDetailsViewModel

    init(viewModel: CardDetailsViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        BlueprintScrollView {
            VStack(spacing: .su8) {
                // content mapped from Figma (Section 10)
            }
        }
        .blueprintNavigationTitle("Card Details")
        .blueprintNavigationBar()
    }
}

// 2. ViewModel (Section 2) — ObservableObject, inject protocols via init
@MainActor
final class CardDetailsViewModel: ObservableObject {
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let service: CardDetailsService

    init(service: CardDetailsService) {
        self.service = service
    }
}

// 3. Preview (Section 12) — #Preview macro, mock dependencies
#Preview("CardDetailsView") {
    CardDetailsView(viewModel: CardDetailsViewModel(service: MockCardDetailsService()))
}
```

**Key rules at a glance:**
- Spacing: `.su4`, `.su8`, `.su12`, `.su16`, `.su24`, `.su32` — never hardcoded `CGFloat`
- Colour: `BlueprintColour.*` tokens — never `Color(hex:)` or `UIColor(red:...)`
- Sensitive inputs: `BlueprintSecureField` — never plain `TextField` or `SecureField`
- Zero `import UIKit` in SwiftUI view files
- `[weak self]` in all closures capturing self

---

## Agent Self-Check

Before finalising any generated iOS file:

- [ ] View uses `@StateObject` to own its ViewModel — not `@State` or `@ObservedObject` for owned ViewModels (Section 4)
- [ ] ViewModel is `ObservableObject` with `@Published` state — no raw struct state in views (Section 2)
- [ ] All dependencies injected via protocol parameters in `init` — no singleton access (Section 3)
- [ ] `.blueprintNavigationBar()` modifier present on every screen view (Section 6)
- [ ] All spacing uses `.su*` tokens — zero hardcoded `CGFloat` padding/spacing (Section 7)
- [ ] All colours use `BlueprintColour.*` — zero `Color(hex:)`, `UIColor(red:...)`, or named system colours (Section 8)
- [ ] Sensitive inputs (`password`, `PIN`, `card number`, `CVV`) use `BlueprintSecureField` (Section 16)
- [ ] Zero `import UIKit` in SwiftUI view files (Section 4)
- [ ] `[weak self]` in all closures capturing `self` (Section 16)
- [ ] All user-facing strings use `.localized` or `LocalizedStringKey` (Section 14)
- [ ] `#Preview` macro used — never `PreviewProvider` struct (Section 12)
- [ ] Every interactive element has `.accessibilityLabel` where label is not self-evident from visible text (Section 15)

---

## 1. Module & File Structure

### 1.1 Feature module hierarchy (new pattern)

```
FeatureModules/{FeatureName}/
├── {FeatureName}.xcodeproj/          (standalone Xcode project)
├── {FeatureName}.podspec             (CocoaPod for workspace integration)
├── {FeatureName}/
│   ├── Public/                       (external API: Factory, Router, Dependencies)
│   │   ├── Dependencies/             (protocol definitions for DI)
│   │   ├── {FeatureName}Factory.swift
│   │   ├── {FeatureName}Router.swift
│   │   └── {FeatureName}Dependencies.swift
│   └── Internal/                     (private implementation)
│       ├── {Feature}/
│       │   ├── Views/                ({FeatureName}View.swift — SwiftUI)
│       │   ├── View Models/          ({FeatureName}ViewModel.swift)
│       │   ├── Factory/              (Builder, BuildResult)
│       │   └── Previews/
│       ├── Sections/                 (sub-feature sections, each with View/ViewModel)
│       │   └── {SectionName}/
│       │       ├── View/
│       │       └── ViewModel/
│       ├── Service/                  (API service layer)
│       ├── Requests/                 (API request definitions)
│       └── Task Manager/
├── {FeatureName}Tests/
│   └── {Section}/ViewModel/          (ViewModel unit tests)
└── {FeatureName}Preview/             (Preview-only target with mock data)
```

### 1.2 Legacy app structure (BMB/ directory)

```
BMB/
├── {FeatureName}/
│   ├── View/                         (SwiftUI views or UIKit ViewControllers)
│   ├── ViewModel/                    (ObservableObject ViewModels)
│   ├── Model/                        (Data models)
│   ├── Service/                      (API service layer)
│   └── Component/                    (Reusable sub-views)
├── UI Shell/                         (Tab bar, navigation, routing)
│   ├── Tabs/                         (TabBarItem structs)
│   └── Journey Extensions/           (JourneyManager routing)
└── Authentication/                   (Login, passcode, biometrics)
```

### 1.3 File naming rules

| Artefact | Convention | Example |
|---|---|---|
| SwiftUI screen view | `{FeatureName}View.swift` | `HomeView.swift`, `CardDetailsView.swift` |
| ViewModel | `{FeatureName}ViewModel.swift` | `HomeViewModel.swift` |
| Section view | `{SectionName}View.swift` or `{SectionName}SectionView.swift` | `AccountCardView.swift` |
| Section ViewModel | `{SectionName}ViewModel.swift` | `AccountCardViewModel.swift` |
| Factory | `{FeatureName}Factory.swift` | `HomeFactory.swift` |
| Router protocol | `{FeatureName}Router.swift` | `HomeRouter.swift` |
| Dependencies protocol | `{FeatureName}Dependencies.swift` | `HomeDependencies.swift` |
| Coordinator | `{FeatureName}Coordinator.swift` | `AuthLaunchCoordinator.swift` |
| API service protocol | `APIServiceDataProvider.swift` | — |
| Request definition | `{RequestName}Request.swift` | `RemoteAPIRequest.swift` |
| Unit test | `{ClassName}Tests.swift` | `AccountCardViewModelTests.swift` |
| ViewModifier | `{ModifierName}.swift` | `HomeNavigationBar.swift` |

---

## 2. ViewModel Pattern

ViewModels are classes conforming to `ObservableObject`. State is exposed via `@Published` properties. Views observe via `@StateObject` (owner) or `@ObservedObject` (injected).

```swift
// {FeatureName}ViewModel.swift
import SwiftUI
import BarclaysBlueprint

class {FeatureName}ViewModel: ObservableObject {

    // MARK: - Published State
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var isInterruptPresented: Bool = false
    @Published var isDrawerPresented: Bool = false

    // MARK: - Non-published state (private(set) for read-only access)
    private(set) var tracker: {FeatureName}Trackable?

    // MARK: - Dependencies (injected via init)
    private let router: {FeatureName}Router
    private let service: APIServiceDataProvider

    // MARK: - Init
    init(router: {FeatureName}Router,
         service: APIServiceDataProvider) {
        self.router = router
        self.service = service
    }

    // MARK: - Actions
    func onPrimaryAction() {
        // update state, call service
    }

    func pullToRefresh() async {
        // async refresh
    }

    func onNavigateBack() {
        router.navigateBack()
    }
}
```

**Rules:**
- All UI-driven state uses `@Published`
- Side effects triggered by ViewModel methods, never inside views
- Dependencies injected via `init`, never singletons (reviewers reject singletons for testability)
- Use `async`/`await` for asynchronous operations
- Always call completion handlers on failure paths (prevents infinite spinners)
- Use `[weak self]` in closures to avoid retain cycles

---

## 3. Dependency Injection Pattern

BMB iOS uses **protocol-based DI** with a Public/Internal boundary. No Hilt, no Swinject, no service locators.

### 3.1 Public boundary (consumed by shell/coordinator)

```swift
// Public/{FeatureName}Dependencies.swift
public protocol {FeatureName}Dependencies: AnyObject {
    var apiService: APIServiceDataProvider { get }
    var imageCache: ImageContentCacheable { get }
    var eventListener: {FeatureName}EventListener { get }
}

// Public/{FeatureName}Router.swift
public protocol {FeatureName}Router: AnyObject {
    func navigateBack()
    func navigateTo{NextScreen}()
}

// Public/{FeatureName}Factory.swift
public protocol {FeatureName}Factory {
    func make{FeatureName}View() -> AnyView
}
```

### 3.2 Internal implementation

```swift
// Internal/Factory/{FeatureName}ViewModelBuilder.swift
struct {FeatureName}ViewModelBuilder {
    let dependencies: {FeatureName}Dependencies
    let router: {FeatureName}Router

    func build() -> {FeatureName}ViewModel {
        {FeatureName}ViewModel(
            router: router,
            service: dependencies.apiService
        )
    }
}
```

**Rules:**
- Never use singletons directly — inject via protocol (reviewers flag this for testability)
- Public protocols define the feature's external contract
- Internal implementations are hidden from other modules
- Factory pattern creates ViewModels with all dependencies resolved

---

## 4. View/Screen Pattern

```swift
// Internal/{Feature}/Views/{FeatureName}View.swift
import SwiftUI
import BarclaysBlueprint

struct {FeatureName}View: View {
    @StateObject private var viewModel: {FeatureName}ViewModel

    init(viewModel: {FeatureName}ViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        BlueprintScrollView {
            VStack(spacing: .su8) {
                // content from design
            }
        }
        .blueprintMargin()
        .blueprintExtendedBackground(.neutral100)
        .blueprintNavigationTitle(viewModel.title)
        .blueprintNavigationBackAction {
            viewModel.onNavigateBack()
        }
        .blueprintNavigationBar()
        .blueprintModalCover(isPresented: $viewModel.isInterruptPresented) {
            interruptView
        }
    }
}

// MARK: - Subviews
private extension {FeatureName}View {
    var interruptView: some View {
        BlueprintInterrupt()
    }
}

// MARK: - Preview
#Preview("{FeatureName}") {
    {FeatureName}View(viewModel: Preview{FeatureName}Dependencies().buildViewModel())
}
```

**Rules:**
- Use `@StateObject` for owned ViewModel, `@ObservedObject` for injected ViewModel
- Subviews extracted as `private` computed properties or `@ViewBuilder` methods
- Use `private enum Constants` for layout values (never magic numbers inline)
- MARK comments for code organisation: `// MARK: - Subviews`, `// MARK: - Preview`
- Previews use dedicated preview dependencies (`Preview{FeatureName}Dependencies`)

---

## 5. Navigation Pattern

BMB iOS uses a **hybrid navigation model**: UIKit coordinators bridge into SwiftUI views. New SwiftUI features use `.navigationDestination(isActive:)` with ViewModel-driven state.

### 5.1 Coordinator pattern (UIKit bridge)

```swift
// {FeatureName}Coordinator.swift
class {FeatureName}Coordinator {
    private let navigationController: UINavigationController

    init(navigationController: UINavigationController) {
        self.navigationController = navigationController
    }

    func start() {
        let viewModel = {FeatureName}ViewModel(router: self, service: ...)
        let hostingController = UIHostingController(rootView: {FeatureName}View(viewModel: viewModel))
        navigationController.pushViewController(hostingController, animated: true)
    }
}

extension {FeatureName}Coordinator: {FeatureName}Router {
    func navigateBack() {
        navigationController.popViewController(animated: true)
    }

    func navigateTo{NextScreen}() {
        // push next screen
    }
}
```

### 5.2 SwiftUI navigation (within a feature)

```swift
// ViewModel-driven navigation
.navigationDestination(isActive: $viewModel.shouldNavigateToNext) {
    NextView(viewModel: viewModel.nextViewModel)
}
```

### 5.3 Tab bar routing

```swift
// BMB/UI Shell/Tabs/{TabName}TabBarItem.swift
struct HomeTabBarItem: TabBarItem {
    static let text = "HR_Home_Tab_Title".localized
    static let symbol: BlueprintSymbol = .home
    let id: Int
}
```

**Rules:**
- Views never call `UINavigationController` directly — always via Router protocol
- Navigation state lives in ViewModel (`@Published var shouldNavigate: Bool`)
- Set state BEFORE pushing view controllers (reviewers flag ordering issues)
- Coordinators own the `UINavigationController` reference
- Deep link resolvers live in `BMB/UI Shell/`

---

## 6. BarclaysBlueprint Design System

**Pod:** `BarclaysBlueprint` (v5.35.0)
**Initialisation:** `Blueprint.initialise()` called from AppDelegate
**Architecture:** Chainable `.blueprint*` modifiers on SwiftUI views (Modifiable protocol)
**Content slots:** `BlueprintSlot` (AnyView wrapper) — no generics on components

### 6.1 How Blueprint components work

Every component follows this pattern:
1. **Initialiser** — creates the base component with required content
2. **Chainable modifiers** — configure optional properties (return new copies)
3. **Slot closures** — inject custom content into designated slots

```swift
// Pattern: init + chainable modifiers
BlueprintAccountCard(viewModel.name, balance: viewModel.balance)
    .blueprintAccountCardDescription(viewModel.description)
    .blueprintAccountCardMedia { cardMedia }
    .blueprintAccountCardAction(viewModel.tapAction)
    .blueprintAccountCardMessages { messageView }
```

---

## 7. Blueprint Spacing Tokens

**Never use hardcoded CGFloat values for spacing.** Use Blueprint spacing unit constants.

| Token | Usage |
|---|---|
| `.su4` | Extra-small spacing (4pt) |
| `.su8` | Small spacing (8pt) — most common |
| `.su12` | Small-medium spacing (12pt) |
| `.su16` | Medium spacing (16pt) |
| `.su24` | Large spacing (24pt) |
| `.su32` | Extra-large spacing (32pt) |
| `.su40` | Section-level spacing (40pt) |
| `.su48` | Major section gap (48pt) |
| `.su160` | Hero/banner height (160pt) |

```swift
// ✅ Correct
VStack(spacing: .su8) { ... }
.padding(.top, .su24)

// ❌ Wrong — will be rejected at review
VStack(spacing: 8) { ... }
.padding(.top, 24)
```

These are `CGFloat` extensions, used directly in SwiftUI layout.

---

## 8. Blueprint Colour Tokens

**Never use hardcoded Color values.** Use Blueprint colour tokens.

### 8.1 Standard colours (BlueprintColour enum)

| Token | Usage |
|---|---|
| `.neutral000` | Pure white surface |
| `.neutral100` | Default screen background |
| `.neutral300` | Subtle borders, dividers |
| `.neutral700` | Secondary text |
| `.neutral900` | Strongest contrast |
| `.title` | Primary text / headings |
| `.brand` | Brand blue (Barclays) |
| `.interactive` | Tappable elements, links, buttons |
| `.error` | Error states |
| `.success` | Success states |
| `.warning` | Warning states |
| `.information` | Info banners |
| `.grey` | Borders, separators |
| `.white` | Light backgrounds, card surfaces |
| `.activeBlue` | Primary brand colour (UI elements) |
| `.darkBlue` | Dark brand variant (headers) |
| `.ghost(.light)` | Skeleton loading placeholder (light) |
| `.ghost(.dark)` | Skeleton loading placeholder (dark) |

### 8.2 Usage patterns

```swift
// ✅ Correct — Blueprint background modifier
.blueprintExtendedBackground(.neutral100)

// ✅ Correct — BlueprintText colour parameter
BlueprintText(viewModel.title, colour: .title, scale: .medium, weight: .medium)

// ✅ Correct — Extended colour for UIKit bridge
UIColor(Color.blueprintExtendedColour(.activeBlue))

// ✅ Correct — Theme colour access
BlueprintTheme.blueprint.getColour(.interactive)

// ❌ Wrong — hardcoded
Color.blue
Color(red: 0.0, green: 0.4, blue: 0.8)
```

---

## 9. Blueprint Typography

Text is rendered via `BlueprintText` with scale, weight, and heading parameters.

```swift
// Pattern
BlueprintText("content", colour: .title, scale: .medium, weight: .medium, heading: .h2)
```

| Scale | Usage |
|---|---|
| `.small` | Captions, hints, metadata |
| `.medium` | Standard body text |
| `.large` | Section headings, emphasis |
| `.extraLarge` | Screen titles, hero text |

| Weight | Usage |
|---|---|
| `.regular` | Body text |
| `.medium` | Emphasis, labels |
| `.bold` | Headings |

| Heading | Usage |
|---|---|
| `.h1` | Screen title |
| `.h2` | Section heading |
| `.h3` | Sub-section heading |
| `nil` | Body text (no heading semantics) |

**Font family:** Barclays Effra App (configured via `Blueprint.initialise()`)

---

## 10. Blueprint Compose Component Map

**Pod:** `BarclaysBlueprint` (version from Podfile)

| Figma Element | Blueprint Component | Key Modifier Pattern | Decision Rule |
|---|---|---|---|
| Scrollable content | `BlueprintScrollView` | `.blueprintRefreshable(action:)` | Root scrollable container |
| Navigation bar | `.blueprintNavigationBar()` | `.blueprintNavigationTitle(_:)`, `.blueprintNavigationBackAction {}` | Applied as view modifier chain |
| Nav bar style (home) | `.blueprintNavigationBarStyle(.home)` | `.blueprintNavigationTrailingItem {}` | Homepage only |
| Primary CTA | `BlueprintButton` | `.blueprintButtonStyle(.primary)` | Most prominent action |
| Secondary action | `BlueprintButton` | `.blueprintButtonStyle(.secondary)` | Alternative action |
| Standard text input | `BlueprintTextField` | — | Non-sensitive text entry |
| Sensitive input | `BlueprintSecureField` | `value: $binding, hint:` | Password, CVV, card number |
| Secure code display | `BlueprintSecureCode` | `label:` | Display masked sensitive values |
| Passcode/PIN | `BlueprintKeypad` | — | Numeric PIN entry grid |
| Body text | `BlueprintText` | `colour:, scale:, weight:, heading:` | All text rendering |
| Icon | `BlueprintIcon` | — | Always set accessibility |
| Icon button | `BlueprintIconButton` | — | Button with icon and label |
| Account card | `BlueprintAccountCard` | `.blueprintAccountCardDescription()`, `.blueprintAccountCardMedia {}`, `.blueprintAccountCardAction()` | Account balance/summary display |
| Account tile | `BlueprintAccountTile` | — | Compact account display |
| Mini banner (inline alert) | `BlueprintMiniBanner` | `.blueprintMiniBannerMediaText()` | Status messages within cards |
| Hero alert banner | `BlueprintHeroAlertBanner` | — | Info/success/warning/error |
| Promo banner | `BlueprintPromoBanner` | `.blueprintPromoBannerTitle()`, `.blueprintPromoBannerMedia {}` | Promotional content |
| Miniature tile | `BlueprintMiniatureTile` | `title:` + media slot | Spotlight/carousel items |
| Hero product tile | `BlueprintHeroProductTile` | — | Product tile with gradient |
| Guide panel | `BlueprintGuidePanel` | — | Panel with title, description, image |
| Panel group | `BlueprintPanelGroup` | — | Groups multiple review panels |
| Review panel | `BlueprintReviewPanel` | `title:, description:, slot:, links:` | Key-value display |
| Callout link panel | `BlueprintCalloutLinkPanel` | `title:` + action closure | Tappable info panel |
| Insight card | `BlueprintInsightCard` | — | Carousel info card |
| Separator | `BlueprintSeparator` | `colour:, thickness:, padding:` | Visual dividers |
| Search button | `BlueprintSearchButton` | `accessibilityPrompt:, action:` | Search trigger |
| Search input | `BlueprintSearchInputField` | `placeholder:` | Active search input |
| Dropdown | `BlueprintDropdown` | `selection: $binding, options:` | Single-select picker |
| Label with icon | `BlueprintLabel` | icon + text slots | Label component |
| Quicklink group | `BlueprintQuicklinkGroup` | `quicklinks:` | Quick action links |
| Tab bar | `BlueprintTabBar` | `.symbol:` | App tab navigation |
| Loading spinner | `BlueprintInterrupt` | — | Full-screen loading animation |
| Ghost loading | Ghost loading views | — | Skeleton placeholder |
| Modal cover | `.blueprintModalCover(isPresented:)` | content closure | Modal sheets |
| Drawer sheet | `.blueprintDrawerSheet(title, isVisible:, detent:)` | `drawerContent:` | Bottom drawer |
| Extended background | `.blueprintExtendedBackground(_:)` | `BlueprintColour` | Screen background colour |
| Margin | `.blueprintMargin()` | — | Standard horizontal margins |
| Scroll-based sizing | `.blueprintScrollBasedOnSize()` | — | Content fits within scroll |

### 10.1 BlueprintSymbol (Icons)

```swift
// Tab bar and icon usage
static let symbol: BlueprintSymbol = .home    // home icon
static let symbol: BlueprintSymbol = .pay     // payments icon
static let symbol: BlueprintSymbol = .chat    // chat/help icon
static let symbol: BlueprintSymbol = .discover // products/discover icon
```

### 10.2 BlueprintString

Text content passed to Blueprint components is wrapped in `BlueprintString`:

```swift
BlueprintAccountCard(BlueprintString(account.productName), balance: BlueprintString(account.balance))
```

---

## 11. Custom View Modifiers

BMB iOS uses custom `ViewModifier` structs for reusable modifier chains. This is the preferred pattern for navigation bars and complex modifier combinations.

```swift
// {FeatureName}NavigationBar.swift
import SwiftUI
import BarclaysBlueprint

struct {FeatureName}NavigationBar: ViewModifier {
    @ObservedObject var viewModel: {FeatureName}ViewModel

    func body(content: Content) -> some View {
        content
            .blueprintNavigationTitle(viewModel.title)
            .blueprintNavigationBarStyle(.standard)
            .blueprintExtendedBackground(.neutral100)
            .blueprintNavigationBackAction {
                viewModel.onNavigateBack()
            }
            .blueprintNavigationBar()
    }
}

extension View {
    func {featureName}NavigationBar(viewModel: {FeatureName}ViewModel) -> some View {
        modifier({FeatureName}NavigationBar(viewModel: viewModel))
    }
}
```

### 11.1 Conditional modifier pattern (`.modify`)

```swift
// Conditional application of modifiers
.modify(where: viewModel.isPowerActionsEnabled) { cardView in
    cardView.blueprintAccountCardActions { actionsView }
}

// With optional value
.modify(using: viewModel.optionalTitle, content: { view, title in
    view.blueprintDrawerSheet(title, ...)
})
```

---

## 12. Preview Pattern

All previews use `#Preview` macro with descriptive labels and dedicated mock dependencies.

```swift
// MARK: - Preview
#Preview("{FeatureName} Default State") {
    {FeatureName}View(viewModel: Preview{FeatureName}Dependencies().buildViewModel())
}

#Preview("{FeatureName} Loading") {
    {FeatureName}View(viewModel: Preview{FeatureName}Dependencies().buildLoadingViewModel())
}
```

**Preview dependencies:**

```swift
// {FeatureName}Preview/{FeatureName}PreviewDependencies.swift
struct Preview{FeatureName}Dependencies: {FeatureName}Dependencies {
    var apiService: APIServiceDataProvider { MockAPIService() }
    var imageCache: ImageContentCacheable { MockImageCache() }
    var eventListener: {FeatureName}EventListener { MockEventListener() }

    var internalRouter: {FeatureName}Router { Mock{FeatureName}Router() }
}
```

**Rules:**
- Use `#Preview` macro (modern syntax), NOT `PreviewProvider` struct
- Descriptive preview names in quotes
- Preview dependencies inject mocks — never real services
- Multiple previews for different states

---

## 13. Testing Patterns

### 13.1 ViewModel unit test

```swift
// {FeatureName}Tests/{Section}/ViewModel/{ClassName}Tests.swift
import XCTest
@testable import {FeatureName}

final class {FeatureName}ViewModelTests: XCTestCase {

    private var sut: {FeatureName}ViewModel!
    private var mockRouter: Mock{FeatureName}Router!
    private var mockService: MockAPIServiceDataProvider!

    override func setUp() {
        super.setUp()
        mockRouter = Mock{FeatureName}Router()
        mockService = MockAPIServiceDataProvider()
        sut = {FeatureName}ViewModel(router: mockRouter, service: mockService)
    }

    override func tearDown() {
        sut = nil
        mockRouter = nil
        mockService = nil
        super.tearDown()
    }

    func test_initialState_isCorrect() {
        XCTAssertFalse(sut.isLoading)
        XCTAssertNil(sut.errorMessage)
    }

    func test_onPrimaryAction_updatesState() {
        sut.onPrimaryAction()
        // assert expected state change
    }

    func test_onNavigateBack_callsRouter() {
        sut.onNavigateBack()
        XCTAssertTrue(mockRouter.navigateBackCalled)
    }
}
```

### 13.2 Test naming convention

```swift
func test_{methodOrProperty}_{condition}() { ... }
// Examples:
func test_pullToRefresh_setsIsLoadingTrue()
func test_onPrimaryAction_whenServiceFails_setsErrorMessage()
```

### 13.3 Test infrastructure

| Component | Framework |
|---|---|
| Unit tests | XCTest |
| Mocking | Manual mock classes (no third-party mocking framework) |
| UI tests | XCUITest |
| Test plan | `.xctestplan` files |
| Coverage | Slather |
| Quality gates | SonarQube |
| Test stubs | `BarclaysTestStubs` (submodule) |

**Rules:**
- All new business logic files MUST have test cases (reviewers enforce this)
- Test feature switch on AND off conditions
- Never leave test/debug code (hardcoded returns) in production code
- Use tearDown to nil out references (prevents retain cycles in tests)

---

## 14. Localisation

All user-facing strings must use the localisation pattern:

```swift
// Localisation key pattern
"HR_Home_Tab_Title".localized

// Dedicated Localization structs (per feature)
enum BMB{FeatureName}Localization {
    static let screenTitle = "{KEY}".localized
    static let primaryAction = "{KEY}".localized
}
```

**Rules:**
- Never hardcode user-visible strings
- Localisation keys follow `{DOMAIN}_{Feature}_{Element}_{Purpose}` format
- Access via `.localized` String extension
- Group related keys in a feature-scoped enum

---

## 15. Accessibility Rules (iOS-specific)

These supplement `barclays-buk-standards:accessibility`:

- Every interactive element has `.accessibilityLabel` if label is not self-evident from visible text
- Heading-level text uses `heading:` parameter on `BlueprintText` (`.h1`, `.h2`, `.h3`)
- Custom sensitive-data views have **redacted** `accessibilityLabel` — never expose full account numbers, card numbers, or sort codes to VoiceOver
- `BlueprintSearchButton` always has `accessibilityPrompt:` set
- Error states must include descriptive text — never colour alone
- Ghost loading views should be hidden from accessibility (`accessibilityHidden(true)`)
- Measurement/hidden views must set `.accessibilityHidden(true)`

```swift
// ✅ Correct — redacted accessibility
accountNumberLabel.accessibilityLabel = "Account number ending \(last4)"

// ✅ Correct — BlueprintText with heading semantics
BlueprintText(sectionTitle, colour: .title, scale: .large, weight: .bold, heading: .h2)

// ❌ Wrong — exposes full PII to VoiceOver
accountNumberLabel.accessibilityLabel = fullAccountNumber
```

---

## 16. Security Rules (iOS-specific)

These supplement `barclays-buk-standards:security`:

- `BlueprintSecureField` for: passwords, PINs, card numbers, CVV, sort codes, account numbers, date of birth, national insurance numbers
- `BlueprintKeypad` for numeric PIN entry — NEVER a custom implementation
- NEVER `TextField` or `SecureField` for any input that could hold PII or financial data
- NEVER `print()` or `NSLog()` with account numbers, card data, or tokens
- NEVER store sensitive state in `@AppStorage` or `UserDefaults` — use ViewModel only
- `.blueprintModalCover` for sensitive modals — never store `isPresented` Bool outside ViewModel
- Use `[weak self]` in ALL closures to avoid retain cycles (reviewers flag 100% of violations)

---

## 17. Code Review Enforcement Patterns

These are patterns enforced by iOS reviewers based on MR review analysis:

### Architecture
- Prefer `struct` over `class` for data mappers and stateless types
- Prefer protocols over concrete classes for presenters and error handlers
- Method naming must reflect all responsibilities (Single Responsibility)
- Move business logic into model extensions for self-documenting code
- Consider existing APIs/closures before creating new ones

### State Management
- Always call completion handlers on ALL paths (including failure) — prevents infinite spinners
- Set navigation state BEFORE pushing view controllers
- Never use direct singleton access — inject via protocol
- Thread safety: justify synchronous barriers; sequential execution is default

### Code Quality
- Use `.first` instead of `[0]` for array access
- Use `.joined(separator:)` over string concatenation
- Remove `print` statements before merge
- Use `nil` for optional closures rather than empty closures `{}`
- Naming: avoid "Helper" suffix (use "Handler"), avoid abbreviations
- Never crash the app — return default/empty instead of force-unwrapping
- Empty string nil-coalescing is banned — keep optionals and safely unwrap
- Remove unused `Foundation` imports
- Use BDL/Blueprint components instead of raw UIKit (UILabel → BlueprintText, UIButton → BlueprintButton)
- Create `static` constants instead of magic numbers/strings

### Memory Management
- `[weak self]` in ALL closure captures that reference `self`
- `nil` out references in `tearDown()` in tests
- Never retain `UINavigationController` without `weak`

---

## 18. API Result Pattern

Use Swift's `Result` type or custom async patterns for API state:

```swift
// Public/Dependencies/APIServiceResult.swift
public enum APIServiceResult {
    case success(Data)
    case failure(APIError)
}

public protocol APIServiceDataProvider: AnyObject {
    func loadCachedData(for request: any CachedAPIRequest) async -> APIServiceResult
    func loadRemoteData(for request: any RemoteAPIRequest) async -> APIServiceResult
}
```

In the ViewModel:
```swift
func loadData() async {
    isLoading = true
    let result = await service.loadRemoteData(for: MyRequest())
    switch result {
    case .success(let data):
        // parse and update state
        isLoading = false
    case .failure(let error):
        errorMessage = error.localizedDescription
        isLoading = false
    }
}
```

---

## 19. Tracking/Analytics Pattern

Every screen and interaction has tracking via a protocol-based tracker:

```swift
// {FeatureName}Trackable protocol
protocol {FeatureName}Trackable {
    func trackLandingPage(with pageVersion: String)
    func trackBackAction(with pageVersionInteraction: String)
    func trackEventAction(with actionName: String, eventMethod: String)
}
```

Usage in views:
```swift
.onAppear {
    viewModel.tracker?.trackLandingPage(with: viewModel.pageVersion)
}
```

**Rules:**
- Tracking calls go in `.onAppear` for page views
- Action tracking in ViewModel methods (not directly in view tap handlers)
- Use optional chaining (`tracker?.track...`) — tracker may be nil in previews/tests

---

## 20. Plugin Scope, Outputs, and Quality Gates

### 20.1 Platform scope

| Channel | Supported |
|---|---|
| Online Banking (native iOS) | Yes |
| Mobile (native iOS) | Yes |
| Android | No — use `barclays-buk-ui-engineer-android` |

### 20.2 Output artefacts

| Artefact | Path | Description |
|---|---|---|
| View file | `{PROJECT_PATH}/{MODULE_NAME}/Internal/Views/{ComponentName}View.swift` | SwiftUI view with BarclaysBlueprint components |
| ViewModel file | `{PROJECT_PATH}/{MODULE_NAME}/Internal/View Models/{ComponentName}ViewModel.swift` | `ObservableObject` — state derived from OAS schema, injected use-case protocols |
| Completion report | `{PROJECT_PATH}/UI_ENGINEER_IOS_COMPLETE.md` | Summary of screens generated, flags, suggested next steps |
| Execution log | `{PROJECT_PATH}/logs/ui-engineer-ios.log` | Timestamped log of all agent actions |

### 20.3 Quality gates (in execution order)

| Gate | Check | Threshold |
|---|---|---|
| Swift compile | `xcodebuild build` or `swift build` | Exit 0 |
| Iron Rule validation | 12 rules (Sections 4, 2) | 0 critical violations |
| Accessibility | `barclays-buk-standards:accessibility` + Section 15 iOS rules | 0 critical violations |
| Security | `barclays-buk-ui-engineer-ios:security-ios` rules | 0 critical violations |

### 20.4 Handoff criteria

| Gate | Why |
|---|---|
| Tested against a real `BarclaysBlueprint` iOS project | BarclaysBlueprint API must be validated against the version in use — component names and modifiers change |
| `xcodebuild build` passes on first attempt for all generated files | Swift compile errors in generated output are a blocker |
| `BlueprintScreenProtection` correctly applied to sensitive screens only | Over-applying breaks accessibility (navigation elements hidden); under-applying is a security risk |
| ViewModel state fields match OAS response schema on a real spec | ViewModel generation must be validated against a real contract |
| `BlueprintSecureField` used for all sensitive inputs | iOS-specific security requirement; critical severity |

### 20.5 Definition of done

- [ ] Every view has a corresponding `{ComponentName}ViewModel.swift` alongside it
- [ ] `BlueprintScreenProtection` applied to all and only screens that display sensitive data
- [ ] `BlueprintSecureField` used for all password, PIN, and card number inputs
- [ ] Zero `import UIKit` in generated view files
- [ ] All user-facing strings use `.localized` / `LocalizedStringKey`
- [ ] Swift build exits 0 on first attempt
