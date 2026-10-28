# Android UI Skill — BMB Jetpack Compose Patterns

> **Source:** bmb-android repository (barclays/mobile-client/android/app/bmb-android)
> **Owner:** BUK Mobile Engineering
> **Review trigger:** Blueprint Compose version bump, quarterly architecture review
> **Last reviewed:** 2026-07-21

This skill encodes the structural patterns used in the Barclays Mobile Banking (BMB) Android codebase. Every generated file must comply with these patterns. Deviations produce code that will not compile or will be rejected at code review.

---

## Quick Start

```kotlin
// Typical generation task: one screen composable + ViewModel + NavGraph

// 1. Screen composable (Section 5) — root is always BlueprintScaffold
@Composable
fun CardDetailsScreen(viewModel: CardDetailsViewModel = ...) {
    BlueprintScaffold(
        navBar = { BlueprintStandardNavBar(title = "Card Details", ...) }
    ) {
        // content
    }
}

// 2. ViewModel (Section 2) — state via mutableStateOf, never remember{} in composable
class CardDetailsViewModel : ViewModel() {
    var isLoading by mutableStateOf(false)
        private set
}

// 3. NavGraph (Section 7) — wrap NavHost with BlueprintTheme
@Composable
fun CardDetailsNavGraph(navController: NavHostController) {
    BlueprintTheme {
        NavHost(navController, startDestination = CardDetailsRoutes.cardDetails) {
            composable(CardDetailsRoutes.cardDetails) { CardDetailsScreen() }
        }
    }
}

// 4. Routes (Section 8) — lowercase snake_case constants
object CardDetailsRoutes {
    const val cardDetails = "card_details"
}
```

**Key rules at a glance:**
- Theme tokens: `LocalColors.current.*`, `LocalSpacing.current.*`, `LocalTypography.current.*` — never `BlueprintTheme.colors.*`
- Blueprint components only — never raw Material/Compose primitives for UI chrome
- Version catalog references: `blueprint.*`, `core.*` — never `libs.*`
- `clearAndSetSemantics {}` is banned — use `semantics {}` instead

---

## Agent Self-Check

Before finalising any generated Android file:

- [ ] Screen root is `BlueprintScaffold` (Section 5) — never `Scaffold` or `Surface`
- [ ] NavBar variant chosen correctly — `BlueprintStandardNavBar` default, `BlueprintLargeNavBar` for information-heavy screens (Section 5)
- [ ] All colours use `LocalColors.current.*` — zero `BlueprintTheme.colors.*` or hardcoded hex (Section 9)
- [ ] All spacing uses `LocalSpacing.current.*` — zero hardcoded `dp` values (Section 9)
- [ ] All typography uses `LocalTypography.current.*` (Section 9)
- [ ] No `remember { mutableStateOf(...) }` inside composables — state lives in ViewModel (Section 2)
- [ ] `ViewModelFactory` uses `ViewModelProvider.Factory` pattern — no Hilt/Koin (Section 3)
- [ ] Navigator is a typed interface — no direct `navController.navigate()` calls in composables (Section 6)
- [ ] `NavHost` wrapped in `BlueprintTheme` (Section 7)
- [ ] All `@Preview` composables use `BlueprintMobilePreview` wrapper (Section 11)
- [ ] Sensitive inputs use `BlueprintSecureField` — never plain `TextField` for PAN/PIN/password (Section 16)
- [ ] No PII (account numbers, sort codes, NI numbers) in `Log.d` / `Log.e` calls (Section 16)
- [ ] Accessibility semantics applied to interactive elements (Section 15)
- [ ] Version catalog references use named catalogs — never bare `libs.*` (Section 1)

---

## 1. Module & File Structure

### 1.1 Team-module hierarchy

```
{teamname}team/
├── appwide/                         # App-wide features shared across all products
├── highlevel/                       # Business logic coordination
├── lowlevel/
│   └── {featurename}/               # One sub-module per feature
│       ├── src/main/java/com/barclays/mobilebanking/{feature}/
│       │   ├── components/          # Reusable sub-composables for this feature
│       │   ├── screens/             # Screen-level composables
│       │   │   └── {FeatureName}NavGraph.kt
│       │   ├── {FeatureName}ViewModel.kt
│       │   ├── {FeatureName}ViewModelFactory.kt
│       │   ├── {FeatureName}Navigator.kt
│       │   ├── {FeatureName}Routes.kt
│       │   └── {FeatureName}Scope.kt
│       └── src/test/java/com/barclays/mobilebanking/{feature}/
│           ├── {FeatureName}ViewModelTest.kt
│           └── screens/{FeatureName}ScreenTest.kt
└── {teamname}.gradle
```

### 1.2 File naming rules

| Artefact | Convention | Example |
|---|---|---|
| Screen composable | `{FeatureName}Screen.kt` or `{FeatureName}Route.kt` | `CardDetailsScreen.kt` |
| NavGraph | `{FeatureName}NavGraph.kt` | `CardDetailsNavGraph.kt` |
| ViewModel | `{FeatureName}ViewModel.kt` | `CardDetailsViewModel.kt` |
| ViewModelFactory | `{FeatureName}ViewModelFactory.kt` | `CardDetailsViewModelFactory.kt` |
| Navigator | `{FeatureName}Navigator.kt` | `CardDetailsNavigator.kt` |
| Routes constants | `{FeatureName}Routes.kt` | `CardDetailsRoutes.kt` |
| DI Scope | `{FeatureName}Scope.kt` | `CardDetailsScope.kt` |
| UI state data class | `{FeatureName}UiState.kt` | `CardDetailsUiState.kt` |
| API result sealed class | `{FeatureName}ApiResultState.kt` | `CardDetailsApiResultState.kt` |
| ViewModel unit test | `{FeatureName}ViewModelTest.kt` | `CardDetailsViewModelTest.kt` |
| Screen composable test | `{FeatureName}ScreenTest.kt` | `CardDetailsScreenTest.kt` |

---

## 2. ViewModel Pattern

State lives in the ViewModel using `mutableStateOf`. **Never pass a UiState data class into a composable as a parameter.** Composables access state directly from the ViewModel via `with(viewModel)`.

```kotlin
// {FeatureName}ViewModel.kt
internal class {FeatureName}ViewModel(
    private val navigator: {FeatureName}Navigator,
    // additional dependencies
) : ViewModel() {

    var isLoading: Boolean by mutableStateOf(false)
        private set

    var errorMessage: String? by mutableStateOf(null)
        private set

    // screen-specific state fields
    var accountName: String by mutableStateOf("")
        private set

    fun onPrimaryAction() {
        // update state
    }

    fun onNavigateBack() {
        navigator.onBackPressed()
    }
}
```

**Rules:**
- All state fields use `by mutableStateOf(...)` with `private set`
- Use `var` not `val` for mutable state fields
- Side effects triggered by ViewModel methods, never inside composables
- `StateFlow` is acceptable for async streams (collected with `.collectAsState()`)

---

## 3. ViewModelFactory Pattern

BMB uses manual DI via `ViewModelProvider.Factory`. There is no Hilt or Koin.

```kotlin
// {FeatureName}ViewModelFactory.kt
internal class {FeatureName}ViewModelFactory(
    private val navigator: {FeatureName}Navigator,
    // additional dependencies from Scope
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        return when {
            modelClass.isAssignableFrom({FeatureName}ViewModel::class.java) ->
                {FeatureName}ViewModel(
                    navigator = navigator,
                ) as T
            else -> throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
        }
    }
}
```

---

## 4. Scope-Based Dependency Injection

Dependencies are resolved via a custom `BaseScope` object. There is no Hilt.

```kotlin
// {FeatureName}Scope.kt
object {FeatureName}Scope : BaseScope() {
    @JvmStatic
    fun getInstance(): {FeatureName}Scope = this
}
```

To retrieve a dependency in a factory or composable:
```kotlin
val someService = {FeatureName}Scope.getInstance()[SomeService::class.java]
```

---

## 5. Composable Screen Pattern

```kotlin
// screens/{FeatureName}Screen.kt
@Composable
internal fun {FeatureName}Screen(
    modifier: Modifier = Modifier,
    viewModel: {FeatureName}ViewModel = viewModel(
        factory = {FeatureName}ViewModelFactory(
            navigator = {FeatureName}Navigator(...)
        )
    )
) {
    with(viewModel) {
        BlueprintScaffold(
            modifier = modifier,
            top = {
                BlueprintStandardNavBar(
                    title = "{Screen Title}",
                    back = BlueprintBackAction(onClick = ::onNavigateBack)
                )
            }
        ) { contentPadding ->
            // Screen content — access viewModel state directly via `with` scope
            // e.g. accountName, isLoading, errorMessage
        }
    }
}
```

**NavBar selection rules:**

| Context | Component |
|---|---|
| Standard journey screen (most screens) | `BlueprintStandardNavBar` |
| Information-heavy / long-title screen | `BlueprintLargeNavBar` |
| Homepage / root screen | `BlueprintHomepageNavBar` |
| No back action needed | Omit `back` parameter |

---

## 6. Navigator Pattern

Each feature defines a typed Navigator. Composables never call `navController.navigate()` directly.

```kotlin
// {FeatureName}Navigator.kt
internal class {FeatureName}Navigator(
    private val navController: NavHostController,
    private val onBackPressedDispatcher: OnBackPressedDispatcher? = null
) {
    fun navigateTo{NextScreen}() {
        navController.navigate({FeatureName}Routes.{NEXT_SCREEN_DESTINATION})
    }

    fun onBackPressed() {
        onBackPressedDispatcher?.onBackPressed() ?: navController.popBackStack()
    }
}
```

---

## 7. NavGraph Pattern

```kotlin
// {FeatureName}NavGraph.kt
@Composable
internal fun {FeatureName}NavGraph(
    // rememberNavController() default is for @Preview only — the real NavGraph wires
    // in the NavController from the host Activity/Fragment, preventing a new instance
    // on every recomposition. Do not use this default in production call sites.
    navHostController: NavHostController = rememberNavController(),
    startDestination: String = {FeatureName}Routes.{START_DESTINATION}
) {
    BlueprintTheme(
        isDarkTheme = isBlueprintDarkTheme(),
        app = configureBlueprintTheme()
    ) {
        NavHost(
            navController = navHostController,
            startDestination = startDestination
        ) {
            {featureName}Screen(navController = navHostController)
            // additional destinations
        }
    }
}

private fun NavGraphBuilder.{featureName}Screen(navController: NavHostController) {
    composable(route = {FeatureName}Routes.{START_DESTINATION}) {
        {FeatureName}Screen(
            viewModel = viewModel(
                factory = {FeatureName}ViewModelFactory(
                    navigator = {FeatureName}Navigator(navController = navController)
                )
            )
        )
    }
}
```

---

## 8. Routes Constants

```kotlin
// {FeatureName}Routes.kt
internal object {FeatureName}Routes {
    const val {START_DESTINATION} = "{feature_name}_start"
    const val {SECOND_DESTINATION} = "{feature_name}_second"
}
```

Route values are lowercase snake_case strings.

---

## 9. Theme Tokens — Correct References

**Never use `BlueprintTheme.colors.*`.** The correct references are:

| Token type | Correct reference | Wrong reference |
|---|---|---|
| Colours | `LocalColors.current.{token}` | `BlueprintTheme.colors.*` |
| Spacing | `LocalSpacing.current.{token}` | hardcoded `dp` values |
| Typography | `LocalTypography.current.{style}` | hardcoded `sp` values or `TextStyle(...)` |

Common colour tokens: `neutral100`, `neutral200`, `neutral300`, `primary`, `error`, `success`, `onSurface`
Common spacing tokens: `small`, `medium`, `large`, `xSmall`, `xLarge`
Common typography styles: `standard`, `small`, `large`, `extraLarge`, `heading`

```kotlin
// Correct
containerColor = LocalColors.current.neutral100
padding(vertical = LocalSpacing.current.small)
style = LocalTypography.current.standard

// Wrong — will fail code review
containerColor = BlueprintTheme.colors.neutral100
padding(vertical = 8.dp)
```

---

## 10. Blueprint Compose Component Map

Dependency: `com.barclays.compose.blueprint:ui` (version from `blueprint.versions.toml`)

| Figma Element | Blueprint Component | Import Path | Decision Rule |
|---|---|---|---|
| Screen root | `BlueprintScaffold` | `com.barclays.compose.blueprint.layout.scaffold` | Always root |
| Nav bar (standard) | `BlueprintStandardNavBar` | `com.barclays.compose.blueprint.components.navigationbar.standard` | Default for most screens |
| Nav bar (large title) | `BlueprintLargeNavBar` | `com.barclays.compose.blueprint.components.navigationbar.large` | Long titles / info screens |
| Nav bar (homepage) | `BlueprintHomepageNavBar` | `com.barclays.compose.blueprint.components.navigationbar.homepage` | Root / dashboard screens |
| Primary CTA | `BlueprintButton` + `blueprintPrimaryButton()` | `com.barclays.compose.blueprint.components.button` | Most prominent action |
| Secondary action | `BlueprintButton` + `blueprintSecondaryButton()` | `com.barclays.compose.blueprint.components.button` | Alternative action |
| Destructive action | `BlueprintButton` + `blueprintPrimaryDangerButton()` | `com.barclays.compose.blueprint.components.button` | Delete / cancel destructive |
| Standard text input | `BlueprintInputField` | `com.barclays.compose.blueprint.components.inputfield` | Non-sensitive text |
| Sensitive input | `BlueprintSecureField` | `com.barclays.compose.blueprint.components.securefield` | Password, card number, sort code |
| Passcode / PIN | `BlueprintPasscodeIndicator` + `BlueprintKeypad` | `com.barclays.compose.blueprint.components.passcodeindicator` | Numeric PIN entry |
| Body text | `BlueprintText` style `LocalTypography.current.standard` | `com.barclays.compose.blueprint.components.text` | Standard paragraph |
| Heading | `BlueprintText` style `LocalTypography.current.large` | `com.barclays.compose.blueprint.components.text` | Screen / section titles |
| Caption | `BlueprintText` style `LocalTypography.current.small` | `com.barclays.compose.blueprint.components.text` | Hints, metadata |
| Tappable list row | `BlueprintTile` with `onClick` | `com.barclays.compose.blueprint.components.tile` | Any tappable row |
| Static card | `BlueprintCard` | `com.barclays.compose.blueprint.components.card` | Non-interactive content block |
| Account card | `BlueprintAccountCard` | `com.barclays.compose.blueprint.components.accountcard` | Account balance / summary card |
| Collapsible section | `BlueprintAccordion` | `com.barclays.compose.blueprint.components.accordion` | Expandable content |
| Mini banner | `BlueprintMiniBanner` | `com.barclays.compose.blueprint.components.banner` | Inline status / alert |
| Hero banner | `BlueprintHeroBanner` | `com.barclays.compose.blueprint.components.banner` | Prominent promotional banner |
| Message banner | `BlueprintMessageBanner` | `com.barclays.compose.blueprint.components.banner` | Inline messaging |
| Alert dialog | `BlueprintAlertDialog` | `com.barclays.compose.blueprint.components.dialog` | Confirmation / destructive confirm |
| Loading dialog | `BlueprintLoadingDialog` | `com.barclays.compose.blueprint.components.dialog` | Full-screen loading overlay |
| Outcome overlay | `BlueprintOutcomeOverlay` | `com.barclays.compose.blueprint.components.overlay` | Success / error full-screen state |
| Progress bar | `BlueprintProgressBar` | `com.barclays.compose.blueprint.components.progressbar` | Linear progress |
| Progress tracker | `BlueprintProgressTracker` | `com.barclays.compose.blueprint.components.progresstracker` | Step-based progress |
| Loading skeleton | `BlueprintGhostLoading` | `com.barclays.compose.blueprint.components.ghostloading` | Content placeholder / skeleton |
| Notification badge | `BlueprintNotificationBadge` | `com.barclays.compose.blueprint.components.badge` | Unread count badge |
| Icon | `BlueprintIcon` | `com.barclays.compose.blueprint.components.icon` | Always set `tint` explicitly |
| Search input | `BlueprintSearchField` | `com.barclays.compose.blueprint.components.searchfield` | Search / filter |
| Dropdown | `BlueprintDropdown` | `com.barclays.compose.blueprint.components.dropdown` | Single-select |
| Radio group | `BlueprintRadioButtonGroup` | `com.barclays.compose.blueprint.components.radiobutton` | Exclusive selection |
| Checkbox | `BlueprintCheckbox` | `com.barclays.compose.blueprint.components.checkbox` | Multi-select |
| Tabs | `BlueprintTabs` | `com.barclays.compose.blueprint.components.tabs` | Tab navigation |
| Separator | `BlueprintSeparator` | `com.barclays.compose.blueprint.components.separator` | Visual divider |
| Window size padding | `.blueprintWindowSizePadding()` modifier | `com.barclays.compose.blueprint.layout` | Responsive safe-area padding |

---

## 11. Preview Pattern

All `@Preview` composables use `BlueprintMobilePreview` as the wrapper. **Never use a bare `@Preview` without this wrapper.** It ensures theming and responsive layout behave as they would on a device.

```kotlin
@Preview
@Composable
private fun {FeatureName}ScreenPreview() {
    BlueprintMobilePreview {
        {FeatureName}Screen()
    }
}
```

Import: `com.barclays.compose.blueprint.preview.BlueprintMobilePreview`

---

## 12. API Result State Pattern

Use a sealed class for async/API states. Use a plain data class for synchronous screen state.

```kotlin
// {FeatureName}ApiResultState.kt — for async data
sealed class {FeatureName}ApiResultState {
    data object Loading : {FeatureName}ApiResultState()
    data class Success(val data: {FeatureName}Data) : {FeatureName}ApiResultState()
    data class Error(val errorUiState: {FeatureName}ErrorUiState) : {FeatureName}ApiResultState()
}
```

In the ViewModel, expose this as a `StateFlow` and collect in the composable:
```kotlin
val apiResultState: StateFlow<{FeatureName}ApiResultState> = ...

// In composable:
val resultState by viewModel.apiResultState.collectAsState()
```

---

## 13. Testing Patterns

### 13.1 Composable UI test

```kotlin
// src/test/java/.../screens/{FeatureName}ScreenTest.kt
@RunWith(RobolectricTestRunner::class)
@Config(instrumentedPackages = ["androidx.loader.content"])
@OptIn(ExperimentalTestApi::class)
class {FeatureName}ScreenTest {

    @MockK
    private lateinit var viewModel: {FeatureName}ViewModel

    @Composable
    private fun Setup(modifier: Modifier = Modifier) {
        MockKAnnotations.init(this, relaxUnitFun = true)
        {FeatureName}Screen(
            modifier = Modifier.testTag(TEST_TAG).then(modifier),
            viewModel = viewModel
        )
    }

    @Test
    fun `{FeatureName} screen displays expected title`() = runComposeUiTest {
        setContent { Setup() }
        onNodeWithTag(TEST_TAG)
            .onChildAt(0)
            .assertTextEquals(EXPECTED_TITLE)
            .assertIsDisplayed()
    }

    private companion object {
        const val TEST_TAG = "{feature_name}_screen"
        const val EXPECTED_TITLE = "{Expected Title}"
    }
}
```

### 13.2 ViewModel unit test

```kotlin
// src/test/java/.../
{FeatureName}ViewModelTest.kt
class {FeatureName}ViewModelTest {

    @MockK
    private lateinit var navigator: {FeatureName}Navigator

    private lateinit var viewModel: {FeatureName}ViewModel

    @Before
    fun setUp() {
        MockKAnnotations.init(this, relaxed = true)
        viewModel = {FeatureName}ViewModel(navigator = navigator)
    }

    @Test
    fun `initial state is correct`() {
        assertFalse(viewModel.isLoading)
        assertNull(viewModel.errorMessage)
    }

    @Test
    fun `onPrimaryAction updates state`() {
        viewModel.onPrimaryAction()
        // assert expected state change
    }
}
```

### 13.3 Test dependencies (from `tests.versions.toml`)

```kotlin
testImplementation("junit:junit:{version}")
testImplementation("io.mockk:mockk:{version}")
testImplementation("org.robolectric:robolectric:{version}")
testImplementation("androidx.compose.ui:ui-test-junit4:{version}")
testImplementation("com.barclays.compose.blueprint:test-ui:{version}")
```

---

## 14. BlueprintTheme Configuration

When wrapping a `NavHost` or a test composable, always configure the theme:

```kotlin
import com.barclays.mobilebanking.core.ui.configureBlueprintTheme
import com.barclays.mobilebanking.core.ui.isBlueprintDarkTheme
import com.barclays.compose.blueprint.theme.BlueprintTheme

BlueprintTheme(
    isDarkTheme = isBlueprintDarkTheme(),
    app = configureBlueprintTheme()
) {
    // NavHost or composable content
}
```

`configureBlueprintTheme()` returns the correct app variant (`Barclays`, `Barclaycard`, or `Legacy`) based on `FlavorDetails`.

---

## 15. Accessibility Rules (Android-specific)

These supplement `barclays-buk-standards:accessibility`:

- `semantics { contentDescription = "..." }` on any interactive element whose label is not self-evident from visible text
- `semantics { heading() }` on section-level `BlueprintText` headings
- `semantics { stateDescription = "..." }` on elements with dynamic state (e.g. toggle, expanded/collapsed)
- Never convey state through colour alone — always pair with a text or icon change
- All `BlueprintInputField` instances must have an explicit `label` parameter — never rely on `placeholder` alone
- Error text must use `BlueprintText` with `LocalColors.current.error` **plus** descriptive text
- `BlueprintIcon` must always have `contentDescription` set or `contentDescription = null` with `decorative = true` declared explicitly

---

## 16. Security Rules (Android-specific)

These supplement `barclays-buk-standards:security`:

- `BlueprintSecureField` for: passwords, PINs, card numbers, sort codes, account numbers, date of birth, national insurance numbers
- `BlueprintPasscodeIndicator` + `BlueprintKeypad` for numeric PIN entry — NEVER a custom implementation
- NEVER `TextField` or `BasicTextField` for any input that could hold PII or financial data
- NEVER `Log.d/Log.e` with account numbers, card data, or tokens
- NEVER store sensitive state in `rememberSaveable` — use ViewModel only
