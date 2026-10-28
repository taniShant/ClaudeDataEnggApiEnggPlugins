---
name: tba
description: >
    BMB (Barclays Mobile Banking / TBA) codebase knowledge. Covers the module tier
    architecture, team module map, package naming conventions, where new code lives,
    reusable shared utilities, MVVM/StateFlow pattern, navigation interface pattern,
    feature flag usage, and test setup conventions. Load this skill in any agent
    generating or reviewing code for the bmb-android repository.
user-invocable: false
---

# TBA Codebase Knowledge

> **Source:** bmb-android repository (barclays/mobile-client/android/app/bmb-android, master branch, July 2026); exploration of `barclaysMobileBanking/`, `coreteam/`, `community/`, `platformteam/` module trees
> **Owner:** BUK Mobile Engineering
> **Review trigger:** Major architectural change, team restructure, or new shared utility added to coreteam
> **Status:** Reviewed

---

## Quick Start

```
# Placing new code in the right module tier

barclaysMobileBanking/
  {teamname}team/
    appwide/      — DI, app-level config, startup only
    highlevel/    — screens, navigation orchestration
    lowlevel/     — data, domain, low-level UI components
      {featurename}/   ← new features go here

# Package naming
com.barclays.mobilebanking.{feature}

# Shared utilities are in coreteam/ — always check before writing your own:
  coreteam/shared/   — analytics, error handling, formatting
  coreteam/ui/       — shared Blueprint components
  platformteam/      — network, storage, security foundations
```

**Before generating code:** check which tier the feature belongs to (Section 1), confirm the team module exists (Section 2), and verify if a shared coreteam utility covers the need (Section 5).

---

## Section 1: Module Tier Architecture

Every feature in bmb-android is decomposed across four module tiers. A team's modules live under `barclaysMobileBanking/{teamname}team/`:

```
barclaysMobileBanking/
  {teamname}team/
    appwide/      — app-wide concerns: DI, app-level configuration, startup
    highlevel/    — user-facing screens and navigation orchestration
    lowlevel/     — data, domain, and low-level UI components
    internal/     — internal utilities, not consumed outside the team boundary
```

**Rules:**
- `lowlevel` modules are the default location for new feature code (data layer, domain logic, reusable UI components)
- `highlevel` modules orchestrate `lowlevel` outputs into full screens
- `appwide` modules are for DI wiring and app startup only — do not put feature logic here
- `internal` modules are team-private; never add a cross-team dependency on an `internal` module

---

## Section 2: Team Module Map

All teams and their primary domains in `barclaysMobileBanking/`:

| Team directory | Domain |
|---|---|
| `accountdetailsteam/` | Account details, transaction history |
| `accountlistteam/` | Account list, account summary |
| `applyteam/` | Product applications, onboarding flows |
| `authenticateateam/` | Authentication, biometrics, PIN |
| `billpaymentteam/` | Bill payment, standing orders |
| `businessteam/` | Business banking features |
| `cardsteam/` | Card management, freeze/unfreeze |
| `cashbackteam/` | Cashback rewards |
| `contactsupport/` | In-app contact and support flows |
| `coreteam/` | Shared framework utilities (see Section 4) |
| `creditcardteam/` | Credit card account features |
| `cryptoteam/` | Crypto integrations |
| `deepLinkteam/` | Deep link handling and routing |
| `depositeam/` | Deposit accounts |
| `digitalwallet/` | Digital wallet (Apple/Google Pay integration) |
| `financialwellbeingteam/` | Spending insights, financial health |
| `freezeteam/` | Card freeze feature |
| `homepageteam/` | Home screen, account summary tiles |
| `identityteam/` | KYC, identity verification |
| `investmentsteam/` | Investments features |
| `jointaccountteam/` | Joint account management |
| `journeyteam/` | Multi-step journey orchestration |
| `lendingteam/` | Loans, overdrafts, lending products |
| `messagingteam/` | In-app messaging and notifications |
| `mortgageteam/` | Mortgage features |
| `notificationsteam/` | Push notifications, alerts |
| `onboardingteam/` | New customer onboarding |
| `passcodesteam/` | Passcode management |
| `paymentsteam/` | Payments, transfers, beneficiary management |
| `personaldetailsteam/` | Personal details, address, contact info |
| `savingsteam/` | Savings accounts, goals |
| `settingsteam/` | App settings, preferences |
| `switchingteam/` | Current account switching (CASS) |
| `tcteam/` | Terms and conditions |
| `transactionsteam/` | Transaction detail, search, categorisation |

---

## Section 3: Shared Modules

These modules are consumed across team boundaries. Always check for an existing shared utility before creating a new one.

### coreteam/core/utilities — Framework utils
Package: `com.barclays.bmb.framework.utils`
Path: `barclaysMobileBanking/coreteam/core/utilities/src/main/java/com/barclays/bmb/framework/utils/`

Contains base classes and shared infrastructure utilities. Prefer over custom implementations.

### community/core/navigation — Navigation contracts
Package: `com.barclays.mobilebanking.navigation`
Path: `community/core/navigation/src/main/java/com/barclays/mobilebanking/navigation/`

Navigation destination interfaces live here. All inter-feature navigation contracts are defined as interfaces in this module, injected into ViewModels.

### coreteam/core/core — Kotlin/coroutine utilities
Package: `com.barclays.mobilebanking.utils`
Path: `barclaysMobileBanking/coreteam/core/core/src/main/java/com/barclays/mobilebanking/utils/`

Contains `CoroutineUtils`, `KotlinNullSafetyUtils`, string extensions, bundle/intent extensions.

---

## Section 4: Package Naming Conventions

Two root packages are in use — do not mix them for new code:

| Package root | Used for |
|---|---|
| `com.barclays.bmb.*` | Framework modules, coreteam infrastructure, shared utilities |
| `com.barclays.mobilebanking.*` | Feature implementations, team-owned code, domain layer |

**For new feature code:** use `com.barclays.mobilebanking.{team}.{feature}.*`

---

## Section 5: Module Naming Convention

Gradle module names drop the team suffix and replace path separators with hyphens:

```
barclaysMobileBanking/homepageteam/lowlevel/accountlist
→ :homepage-lowlevel-accountlist

barclaysMobileBanking/paymentsteam/highlevel/paymentscreen
→ :payments-highlevel-paymentscreen
```

Source sets within a module follow the standard Android layout:
```
src/main/java/       — production Kotlin
src/test/kotlin/     — unit tests
src/androidTest/     — instrumented tests
```

---

## Section 6: Reusable Shared Utilities

These utilities exist in the shared modules. Use them; do not reimplement.

### 6.1 `safeLet` — Multi-param null-safe let

**Package:** `com.barclays.mobilebanking.utils`

Executes `block` only when all parameters are non-null. Prefer over nested null checks.

```kotlin
// 2-param
fun <T1, T2, R> safeLet(p1: T1?, p2: T2?, block: (T1, T2) -> R?): R?

// 3-param
fun <T1, T2, T3, R> safeLet(p1: T1?, p2: T2?, p3: T3?, block: (T1, T2, T3) -> R?): R?

// Up to 6 params available
```

Usage:
```kotlin
safeLet(userId, accountId) { uid, aid ->
    repository.fetch(uid, aid)
}
```

### 6.2 `asyncAll` — Parallel coroutine execution

**Package:** `com.barclays.mobilebanking.utils`

Launches all items in the collection as concurrent coroutines and awaits all results.

```kotlin
suspend fun <T, R> Iterable<T>.asyncAll(
    dispatcher: CoroutineDispatcher = Dispatchers.IO,
    block: suspend (T) -> R
): List<R>
```

Usage:
```kotlin
val results = accountIds.asyncAll { id -> repository.fetchAccount(id) }
```

### 6.3 `isNullStringValue` / `isNotNullStringValue`

**Package:** `com.barclays.mobilebanking.utils`

String extensions that treat `null`, empty, and the literal string `"null"` as null:

```kotlin
fun String?.isNullStringValue(): Boolean       // true if null, "", or "null"
fun String?.isNotNullStringValue(): Boolean    // inverse
```

### 6.4 `forAll` — Non-null list guard

**Package:** `com.barclays.mobilebanking.utils`

Returns a `List<T>` only if all vararg elements are non-null; returns `null` otherwise:

```kotlin
fun <T : Any> forAll(vararg elements: T?): List<T>?
```

### 6.5 String extensions

**Package:** `com.barclays.mobilebanking.utils`

```kotlin
fun String.removeCommas(): String
fun String.encodeUrl(): String
fun String.decodeUrl(): String
```

### 6.6 Bundle / Intent parcelable extensions

**Package:** `com.barclays.mobilebanking.utils`

```kotlin
// BundleExtensions
inline fun <reified T : Parcelable> Bundle.parcelable(key: String): T?

// IntentExtensions
inline fun <reified T : Parcelable> Intent.parcelable(key: String): T?
inline fun <reified T : Parcelable> Intent.parcelableArrayList(key: String): ArrayList<T>?
```

---

## Section 7: MVVM / StateFlow Pattern

All ViewModels in bmb-android follow this pattern. Generated ViewModels must conform.

### 7.1 State and event model

```kotlin
data class MyFeatureState(
    val isLoading: Boolean = false,
    val data: MyData? = null,
    val error: String? = null
    // Max 6 fields — UiStateComplexity detekt rule
)

sealed class MyFeatureEvent {
    data class LoadData(val id: String) : MyFeatureEvent()
    object Retry : MyFeatureEvent()
}
```

### 7.2 ViewModel structure

```kotlin
class MyFeatureViewModel @Inject constructor(
    private val repository: MyFeatureRepository
) : ViewModel() {

    private val _state = MutableStateFlow(MyFeatureState())
    val state: StateFlow<MyFeatureState> = _state.asStateFlow()

    // Option A — single onEvent dispatcher (common in TBA for complex screens)
    fun onEvent(event: MyFeatureEvent) {
        when (event) {
            is MyFeatureEvent.LoadData -> loadData(event.id)
            MyFeatureEvent.Retry -> retry()
        }
    }

    // Option B — individual public functions (used in some TBA teams)
    fun loadData(id: String) { ... }
    fun retry() { ... }

    private fun loadData(id: String) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            try {
                val data = repository.fetchData(id)
                _state.update { it.copy(isLoading = false, data = data) }
            } catch (e: Exception) {
                _state.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }
}
```

**Rules:**
- `_state` is always `private`; `state` is always `val StateFlow` via `asStateFlow()`
- Both `onEvent(event: T)` (single dispatcher) and individual named public functions are used in TBA — either is acceptable. What is **not** acceptable: exposing raw internal implementation functions publicly, or returning data directly from ViewModel methods (use state for that)
- Events must be handled — reviewers flag unhandled or silently ignored events
- State updates use `_state.update { it.copy(...) }` — never direct assignment
- Coroutines launch in `viewModelScope` only

---

## Section 8: Navigation Pattern

Navigation contracts are defined as interfaces in `community/core/navigation/` and injected into ViewModels via Hilt.

### 8.1 Defining a navigation contract

```kotlin
// In community/core/navigation/src/main/java/com/barclays/mobilebanking/navigation/
interface MyFeatureNavigation {
    fun navigateToDetail(id: String)
    fun navigateBack()
}
```

### 8.2 Consuming navigation in a ViewModel

```kotlin
class MyFeatureViewModel @Inject constructor(
    private val navigation: MyFeatureNavigation,
    private val repository: MyFeatureRepository
) : ViewModel() {

    fun openDetail(id: String) {
        navigation.navigateToDetail(id)
    }
}
```

**Rules:**
- Navigation interfaces are defined in `community/core/navigation/` — never inside a feature module
- ViewModels receive the navigation interface via constructor injection — never hold a reference to NavController
- Composables do not navigate directly — they call ViewModel functions or dispatch events

---

## Section 9: Feature Flags

Feature visibility is controlled via `FeatureHelper`. Always gate new or experimental features.

```kotlin
// Import
import com.barclays.mobilebanking.featureflags.FeatureHelper

// Usage in ViewModel or UseCase
if (FeatureHelper.isFeatureVisible(key = "MY_FEATURE_KEY")) {
    // feature-specific path
}
```

**Rules:**
- Feature keys are backend-driven strings — never hardcode the gating logic
- Check the feature flag at the ViewModel or UseCase layer, not in Composables
- Do not remove feature flag gates until the flag is confirmed rolled out and deleted from the backend

---

## Section 10: Test Setup Conventions

Unit tests use MockK with JUnit4. The following pattern is mandatory.

### 10.1 Standard test class structure

```kotlin
import io.mockk.MockKAnnotations
import io.mockk.every
import io.mockk.impl.annotations.MockK
import io.mockk.verify
import org.junit.Before
import org.junit.Test

class MyFeatureViewModelTest {

    @MockK
    lateinit var mockRepository: MyFeatureRepository

    private lateinit var viewModel: MyFeatureViewModel

    @After
    fun tearDown() {
        unmockkAll()
    }

    @Before
    fun setUp() {
        MockKAnnotations.init(this, relaxed = true)
        viewModel = MyFeatureViewModel(mockRepository)
    }

    @Test
    fun `given valid id when load data then state contains data`() {
        every { mockRepository.fetchData(TEST_ID) } returns TEST_DATA

        viewModel.onEvent(MyFeatureEvent.LoadData(TEST_ID))

        assert(viewModel.state.value.data == TEST_DATA)
    }

    companion object {
        private const val TEST_ID = "test-id-123"
        private val TEST_DATA = MyData(id = TEST_ID)
    }
}
```

**Rules:**
- `MockKAnnotations.init(this, relaxed = true)` in `@Before` — always `relaxed = true` to avoid unspecified stub failures
- `relaxUnitFun = true` is redundant when `relaxed = true` is set — never use both
- Call `unmockkAll()` in `@After` if you use `mockkObject` or `mockkStatic` anywhere in the test class
- Name test helper functions `setup` or `config`, not `mock`: `fun setupUser()` not `fun mockUser()`
- Use `with(viewModel)` scope function to avoid repeating `viewModel.` on every line in setup blocks
- Use `verifyExactly(n) {}` extension instead of `verify(atLeast = N) {}` for exact invocation counts
- All test constants go in the `companion object` — never inline magic strings or values
- Test function names use backtick syntax: `` `given X when Y then Z` `` — reads as a full sentence
- `TestResourceManager` is available for loading JSON fixtures from `src/test/resources/`
- Do not use `mockk<T>()` inline constructors in field declarations — use `@MockK` annotations

---

## Section 11: Build Conventions

### 11.1 Version catalog

All dependency versions are defined in `barclaysMobileBanking/dependencies/*.versions.toml`. Multiple named catalogs are registered in `settings.gradle` — never hardcode version strings, always reference the appropriate catalog alias:

| Catalog alias | TOML file | Used for |
|---|---|---|
| `blueprint.*` | `blueprint.versions.toml` | Blueprint Compose design system |
| `core.*` | `core.versions.toml` | AndroidX core, Kotlin, Hilt, coroutines |
| `lifecycle.*` | `lifecycle.versions.toml` | `lifecycle-viewmodel`, `lifecycle-runtime` |
| `tests.*` | `test.versions.toml` | MockK, JUnit, Espresso, Compose testing |
| `barclays.*` | `barclays.versions.toml` | Barclays internal libraries |
| `support.*` | `support.versions.toml` | AppCompat, Material, Fragment |
| `observability.*` | `observability.versions.toml` | Logging, analytics |
| `playservices.*` | `playservices.versions.toml` | Google Play Services |

```kotlin
// build.gradle.kts — use the correct catalog for each dependency
dependencies {
    implementation(blueprint.compose.ui)
    implementation(core.kotlinx.coroutines.android)
    implementation(lifecycle.viewmodel.ktx)
    testImplementation(tests.mockk)
    testImplementation(tests.junit)
}
```

### 11.2 Standard module build.gradle structure

A typical feature module `build.gradle.kts`:

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("com.google.dagger.hilt.android")
    id("kotlin-kapt")
}

android {
    namespace = "com.barclays.mobilebanking.{feature}"
    compileSdk = libs.versions.compileSdk.get().toInt()
    // ...
}

dependencies {
    implementation(libs.blueprint.compose.ui)
    implementation(libs.hilt.android)
    kapt(libs.hilt.compiler)
    // ...
}
```

---

## Agent Self-Check

Before finalising any generated code for the bmb-android codebase:

- [ ] Package name follows `com.barclays.mobilebanking.{team}.{feature}.*` convention
- [ ] New code placed in the correct tier (`lowlevel` for data/domain/components, `highlevel` for screen orchestration)
- [ ] No dependency declared on another team's `internal` module
- [ ] Reusable utilities (`safeLet`, `asyncAll`, `isNullStringValue`, `forAll`) used instead of reimplemented
- [ ] ViewModel state is `private MutableStateFlow` + `public StateFlow via asStateFlow()`
- [ ] Public ViewModel API is either `onEvent(event: T)` or individual named functions — no raw internal functions exposed, no data returned directly from methods
- [ ] Navigation via injected interface from `community/core/navigation/` — no NavController in ViewModel
- [ ] New/experimental features gated with `FeatureHelper.isFeatureVisible(key)`
- [ ] Feature flag check at ViewModel/UseCase layer, not in Composable
- [ ] Test constants in `companion object`, not inline
- [ ] `MockKAnnotations.init(this, relaxed = true)` in `@Before`
- [ ] Dependency versions referenced from the correct named version catalog (`blueprint.*`, `core.*`, `tests.*`, `barclays.*`, etc. per Section 11.1) — never hardcoded strings
