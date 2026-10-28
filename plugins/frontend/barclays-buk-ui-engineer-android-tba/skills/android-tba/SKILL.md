# Android TBA Skill — The Barclays App–Specific Patterns

This skill extends `barclays-buk-ui-engineer-android:android`. It covers patterns that only exist in the BMB monorepo. Do not duplicate anything from the base `android` skill here — reference it with "follow the android skill" and add only TBA-specific additions.

---

## 1. When to Apply TBA Patterns

Apply TBA patterns when the feature lives inside the BMB monorepo (`barclaysMobileBanking/`) and any of the following are true:

| Trigger | TBA pattern to apply |
|---|---|
| Multi-step user flow (registration, authentication, onboarding) | Journey Framework — Section 2 |
| Next step is determined by an API response | MVC action layer — Section 3 |
| Feature needs to register itself in the team or app navigation | NavigationScope + JourneyFrameworkModuleLauncher — Section 4 |
| Screen or ViewModel behaviour differs between Barclays / Barclaycard / StaffPilot flavors | FlavorDetails — Section 5 |
| Screen is hosted at Activity level (not embedded in an existing NavHost) | BarclaysActivity + Compose hosting — Section 6 |
| Icon name comes from an API response or dynamic source | TbaIconMapper / mapIcon() — Section 7 |
| Activity reference is required inside a Composable | ComposeActivityContext — Section 8 |
| Screen is a journey step that must be tracked in analytics | analyticsPageTag + DynamicViewAnalytics — Section 9 |

For everything else, follow the base `android` skill only.

---

## 2. Journey Framework

### 2.1 What it is

The Journey Framework coordinates multi-step user flows where each step is independently owned by a team module. The framework handles:
- Server-driven next-step routing (API returns which module is next)
- Module lifecycle management
- Mandatory field validation before advancing
- Analytics event firing on each step

### 2.2 Core contracts

**`BaseRegistrationModule`** — data carrier for a single journey step:

```kotlin
class {Feature}Module(content: JourneyFrameworkApiContent?) :
    JourneyFrameworkModuleContract.BaseRegistrationModule {

    override var id: String? = content?.moduleId
    override val mandatoryFields: MutableList<Any?> = mutableListOf()
    override var title: String? = null
    val analyticsPageTag: String = "{FEATURE_ANALYTICS_TAG}"

    // Parse feature-specific data from the API content
    val data: {Feature}ModuleData = {Feature}ModuleData(
        content?.data?.getJSONObject("{feature_data_key}")
    )

    private var actions: List<MvcAction>? = content?.actions

    override fun getAction(id: String?): MvcAction? =
        actions?.firstOrNull { it.id == id }

    override fun attachPayloadToMvcAction() {
        // Attach module-specific payload to the action before execution
    }

    override fun executeActionWithEmptyPayload() {
        getAction(ActionType.NEXT)?.let { action ->
            // Execute with no payload (e.g. skip/cancel actions)
        }
    }
}
```

**`JourneyFrameworkModulePopulator`** — creates the module from API content:

```kotlin
class {Feature}Populator : JourneyFrameworkModulePopulator {
    override fun populate(
        target: JourneyFrameworkModuleContract.InitiateTarget,
        content: JourneyFrameworkApiContent?
    ) {
        target.initiateModule({Feature}Module(content))
    }
}
```

**`ModuleHelper`** — implemented by the Presenter; receives the populated module:

```kotlin
// Implemented on {Feature}Presenter
override fun startModule(registrationModule: JourneyFrameworkModuleContract.BaseRegistrationModule) {
    this.module = registrationModule as {Feature}Module
    // Initialize UI, log analytics start event
    analyticsLogger.logScreenView(module.analyticsPageTag)
}
```

### 2.3 Initialising a journey step

Called from the Activity's `onCreate`:

```kotlin
JourneyFrameworkGenericHelper.initialise(
    {Feature}Populator(),                          // creates the module
    presenter,                                      // implements ModuleHelper
    this,                                           // Activity (LifecycleOwner)
    AuthenticationController.CONTROLLER_ID          // or relevant controller ID
)
```

### 2.4 Advancing to the next step

```kotlin
// In presenter, after collecting user input into payload:
fun onPrimaryAction(userInput: {Feature}RequestData) {
    val action = module.getAction(ActionType.NEXT)
    module.attachPayloadToMvcAction(userInput, action)

    journeyFrameworkHandleActionBuilder.build().executeAction(
        action,
        module.id,
        AuthenticationController.CONTROLLER_ID
    )
}
```

### 2.5 File layout for a journey step

```
{featureteam}/lowlevel/{feature}/src/main/java/{package}/
├── {Feature}Module.kt              — BaseRegistrationModule
├── {Feature}ModuleData.kt          — Parses JSON from API content
├── {Feature}Populator.kt           — JourneyFrameworkModulePopulator
├── {Feature}Presenter.kt           — ModuleHelper + action handling
├── {Feature}Activity.kt            — BarclaysActivity host (see Section 6)
├── screens/
│   ├── {Feature}Screen.kt          — Jetpack Compose screen (base android skill)
│   └── {Feature}NavGraph.kt        — NavGraph (base android skill)
├── {Feature}ViewModel.kt           — base android skill
├── {Feature}ViewModelFactory.kt    — base android skill
├── {Feature}Navigator.kt           — base android skill
└── {Feature}Routes.kt              — base android skill
```

---

## 3. MVC Action Layer

### 3.1 ActionType constants

Always use `ActionType` constants for action IDs — never hardcode strings:

```kotlin
// Correct
val action = module.getAction(ActionType.NEXT)
val cancelAction = module.getAction(ActionType.CANCEL)
val backAction = module.getAction(ActionType.BACK)

// Wrong — never do this
val action = module.getAction("next")
val action = module.getAction("NEXT")
```

### 3.2 JourneyFrameworkGenericHandleAction

The handler is created from a `Builder` that takes an `Activity` reference. It observes the Activity lifecycle to prevent memory leaks — do not hold the handler across configuration changes:

```kotlin
class {Feature}Presenter(
    private val journeyFrameworkHandleActionBuilder: JourneyFrameworkGenericHandleAction.Builder
) {
    fun executeAction(action: MvcAction?) {
        journeyFrameworkHandleActionBuilder
            .build()
            .executeAction(
                action,
                module.id,
                {CONTROLLER_ID}
            )
    }
}
```

Pass `JourneyFrameworkGenericHandleAction.Builder(activity)` from the Activity — never from inside a Composable.

### 3.3 Controller IDs

Use the constant from the relevant controller:

```kotlin
AuthenticationController.CONTROLLER_ID       // auth/registration flows
// Each team defines their own controller ID — check the team's controller class
```

---

## 4. NavigationScope and JourneyFrameworkModuleLauncher

### 4.1 Cross-team navigation

Cross-team navigation is handled via `NavigationScope`, not by passing `NavController` directly. Each team exposes a navigation interface:

```kotlin
// To navigate TO your feature from another team's module launcher entry:
NavigationScope.get({Feature}Navigation::class.java).launch{Feature}Activity(
    activity = activity,
    moduleId = moduleId,
    content = content?.moduleJsonString
)

// Define your navigation interface:
interface {Feature}Navigation {
    fun launch{Feature}Activity(
        activity: Activity,
        moduleId: String?,
        content: String?
    )
}
```

### 4.2 JourneyFrameworkModuleLauncher registration

When your feature is a destination reachable from the Journey Framework, register it in `JourneyFrameworkModuleLauncher`:

```kotlin
// In JourneyFrameworkModuleLauncher.launchModule():
{FeatureTeam}Modules.{FEATURE_MODULE_ID} ->
    NavigationScope.get({Feature}Navigation::class.java)
        .launch{Feature}Activity(activity, moduleId, modelId, content?.moduleJsonString)
```

---

## 5. Scope Hierarchy

### 5.1 Scope levels

| Scope level | Examples | Use for |
|---|---|---|
| App-wide | `CoreScope`, `NavigationScope`, `ModuleDataExchangeScope`, `AuthenticationModuleScope` | Services used across all teams |
| Team-level | `HomepageScope`, `ProfileScope`, `HelpScope`, `AemScope`, `EcosystemScope` | Services owned by a specific team |
| Feature-level | `ContainerOptionsScope`, `VisaCashbackScope`, `AccountsScope` | Services scoped to one feature |

### 5.2 Defining a feature scope

```kotlin
// {Feature}Scope.kt
object {Feature}Scope : BaseScope() {
    @JvmStatic
    fun getInstance(): {Feature}Scope = this
}
```

### 5.3 Registering dependencies

Register in the team's application initialisation (typically in a `{Team}Initialiser` or `Application.onCreate`):

```kotlin
{Feature}Scope.register({Feature}Service::class.java, LazyLoader {
    {Feature}ServiceImpl(CoreScope.get(SomeCoreDependency::class.java))
})
```

### 5.4 Accessing dependencies

```kotlin
// From a ViewModelFactory or Presenter — never from inside a Composable
val service = {Feature}Scope.get({Feature}Service::class.java)

// Team-level access
val analytics = HomepageScope[HomepageUiShellAnalytics::class.java]

// App-level access
val config = CoreScope.get(ApplicationConfig::class.java)
```

**Rule:** Never call `Scope.get(...)` inside a `@Composable` function. Resolve all dependencies in the factory or presenter.

---

## 6. BarclaysActivity — Compose Hosting

When a feature needs its own Activity entry point (i.e. it is launched from `JourneyFrameworkModuleLauncher` or from another team), extend `BarclaysActivity`, not `AppCompatActivity`:

```kotlin
// {Feature}Activity.kt
class {Feature}Activity : BarclaysActivity() {

    private val analyticsLogger: {Feature}Analytics by lazy {
        {Feature}Scope[{Feature}Analytics::class.java]
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Parse any Intent extras passed from JourneyFrameworkModuleLauncher
        val moduleId = intent.getStringExtra(MODULE_ID_KEY)
        val content = intent.getStringExtra(CONTENT_KEY)

        setContent {
            BlueprintTheme(
                isDarkTheme = isBlueprintDarkTheme(),
                app = configureBlueprintTheme(),
                edgeToEdge = true
            ) {
                BackHandler(onBack = ::onBackNavigation)

                // Provide CompositionLocals needed by the screen
                val context = LocalContext.current
                val digitalRegistryLauncher = remember {
                    DigitalRegistryLauncherImpl(activity = context as AppCompatActivity)
                }
                CompositionLocalProvider(
                    LocalDigitalRegistryLauncher provides digitalRegistryLauncher
                ) {
                    {Feature}NavGraph(
                        // Pass initialisation data from Intent
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        analyticsLogger.logScreenView()
    }

    private fun onBackNavigation() {
        finish()
    }

    companion object {
        const val MODULE_ID_KEY = "moduleId"
        const val CONTENT_KEY = "content"
    }
}
```

**Rules:**
- Always extend `BarclaysActivity` — never `AppCompatActivity` directly in BMB
- Always wrap `setContent` body in `BlueprintTheme` with `configureBlueprintTheme()` and `isBlueprintDarkTheme()`
- `edgeToEdge = true` is the standard for new screens
- Parse Intent extras in `onCreate`, not in Composables
- Log analytics in `onResume` to capture re-entries

---

## 7. TbaIconMapper — Dynamic Icon Resolution

Use `mapIcon()` when the icon name comes from an API response or a dynamic source. **Never build a manual `when` block mapping icon strings to `ImageVector` — that is exactly what `mapIcon()` is for.**

```kotlin
import com.barclays.compose.blueprint.tools.TbaIconMapper.mapIcon

// In a Composable — mapIcon() is a @Composable function
BlueprintIcon(
    painter = mapIcon(iconName = item.iconName) ?: rememberVectorPainter(
        BlueprintVectors.Outlined.Placeholder
    ),
    tint = LocalColors.current.onSurface,
    contentDescription = item.accessibilityLabel
)

// With a named Blueprint icon (static, known at compile time) — use the vector directly
BlueprintIcon(
    imageVector = BlueprintVectors.Outlined.ChevronRight,
    tint = LocalColors.current.onSurface,
    contentDescription = null
)
```

**Rules:**
- `mapIcon()` is `@Composable` — call it only inside a composable function
- Always provide a fallback: `mapIcon(...) ?: rememberVectorPainter(BlueprintVectors.Outlined.Placeholder)`
- Always set explicit `tint` — never rely on implicit colour (Iron Rule 11 from the android skill)
- For static, compile-time known icons, use `BlueprintVectors.Outlined.*` directly — no need for `mapIcon()`

---

## 8. ComposeActivityContext — Activity Reference in Composables

When a Composable or ViewModelFactory needs an `AppCompatActivity` reference (e.g. to pass to a legacy navigator or `JourneyFrameworkGenericHandleAction.Builder`), use the extension from `ComposeActivityContext`:

```kotlin
import com.barclays.compose.blueprint.tools.getAppCompatActivity

// Inside a @Composable (avoid if possible — prefer resolving in factory)
val activity = LocalContext.current.getAppCompatActivity()

// Inside a ViewModelFactory (preferred pattern)
class {Feature}ViewModelFactory(
    private val context: Context
) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        val activity = context.getAppCompatActivity()
        return {Feature}ViewModel(
            navigator = {Feature}Navigator(activity)
        ) as T
    }
}

// In a NavGraph composable — pass context before entering composition
composable(route = ...) {
    val context = LocalContext.current
    {Feature}Screen(
        viewModel = viewModel(
            factory = {Feature}ViewModelFactory(context = context)
        )
    )
}
```

**Rules:**
- `getAppCompatActivity()` throws if the context is not an Activity context — only call it when you are certain of the call site
- Annotated `@Discouraged` — minimise usage; resolve in factory rather than inside a Composable body
- Never store the Activity reference in a ViewModel — it causes memory leaks. Pass it to builders (like `JourneyFrameworkGenericHandleAction.Builder`) at the point of use only

---

## 9. Analytics — analyticsPageTag and DynamicViewAnalytics

Every journey step must have an `analyticsPageTag`. This is the analytics identifier used in `DynamicViewAnalytics` to log screen views and user interactions.

### 9.1 Defining the tag

```kotlin
// In the Module
class {Feature}Module(content: JourneyFrameworkApiContent?) :
    JourneyFrameworkModuleContract.BaseRegistrationModule {
    val analyticsPageTag: String = "{FEATURE_ANALYTICS_TAG}"
    // e.g. "personal_details_capture", "biometric_setup", "card_freeze_confirm"
}
```

### 9.2 Logging screen view

```kotlin
// In the Presenter's startModule():
override fun startModule(registrationModule: BaseRegistrationModule) {
    this.module = registrationModule as {Feature}Module
    DynamicViewAnalytics.logScreenView(module.analyticsPageTag)
}
```

### 9.3 Logging user interactions

```kotlin
// In the ViewModel, for user actions with analytics significance:
fun onPrimaryAction() {
    DynamicViewAnalytics.logEvent(
        pageTag = module.analyticsPageTag,
        eventName = "primary_action_tapped"
    )
    // ... proceed with action
}
```

### 9.4 Activity-level analytics

Log screen views in `onResume`, not `onCreate`, to capture re-entries after back navigation:

```kotlin
override fun onResume() {
    super.onResume()
    analyticsLogger.logScreenView()
}
```

---

## 10. FlavorDetails — Product Flavor Branching

`FlavorDetails` is injected at app initialisation via `ApplicationConfig`. Retrieve it from `CoreScope` — never use `BuildConfig` flavor checks directly in feature code.

```kotlin
val flavorDetails: FlavorDetails = CoreScope.get(ApplicationConfig::class.java).flavorDetails
```

**Available checks:**

```kotlin
flavorDetails.isBarclaycard     // true for barclaycard flavor
flavorDetails.isProductionBuild // true for live/slgl environments
flavorDetails.isStubbed         // true for stubbed test environment
flavorDetails.isSit             // true for SIT environment
```

**Pattern for flavor-specific behaviour:**

```kotlin
// In ViewModel or Presenter
private val isBarclaycardFlavor = CoreScope.get(ApplicationConfig::class.java)
    .flavorDetails.isBarclaycard

fun getWelcomeMessage(): String = if (isBarclaycardFlavor) {
    "Welcome to Barclaycard"
} else {
    "Welcome to Barclays"
}
```

**Pattern for flavor-specific source-set overrides:**

Place the overriding implementation in `src/barclaycard/java/...` or `src/barclaysmobilebanking/java/...` rather than branching in shared code. Use a shared interface with flavor-specific implementations:

```kotlin
// src/main/java/.../MigrationFeature.kt
interface MigrationFeature {
    fun isMigrationRequired(): Boolean
}

// src/barclaysmobilebanking/java/.../MigrationFeatureProvider.kt
class MigrationFeatureProvider : MigrationFeature {
    override fun isMigrationRequired(): Boolean = false
}

// src/barclaycard/java/.../MigrationFeatureProvider.kt
class MigrationFeatureProvider : MigrationFeature {
    override fun isMigrationRequired(): Boolean = true
}
```

---

## 11. Testing TBA-Specific Patterns

### 11.1 ComposeActivityContext stubbing in UI tests

When a Composable uses `LocalContext.current.getAppCompatActivity()`, provide a stubbed Activity context:

```kotlin
@RunWith(RobolectricTestRunner::class)
@Config(instrumentedPackages = ["androidx.loader.content"])
@OptIn(ExperimentalTestApi::class)
class {Feature}ScreenTest {

    @MockK
    private lateinit var viewModel: {Feature}ViewModel

    @Composable
    private fun Setup(modifier: Modifier = Modifier) {
        MockKAnnotations.init(this, relaxUnitFun = true)
        // Stub activity context if the composable uses getAppCompatActivity()
        every { (LocalContext.current as? AppCompatActivity) } returns mockk(relaxed = true)
        {Feature}Screen(
            modifier = Modifier.testTag(TEST_TAG).then(modifier),
            viewModel = viewModel
        )
    }
}
```

### 11.2 Testing Journey Framework Presenter

```kotlin
class {Feature}PresenterTest {

    @MockK lateinit var journeyHandleActionBuilder: JourneyFrameworkGenericHandleAction.Builder
    @MockK lateinit var journeyHandleAction: JourneyFrameworkGenericHandleAction
    @MockK lateinit var module: {Feature}Module

    private lateinit var presenter: {Feature}Presenter

    @Before
    fun setUp() {
        MockKAnnotations.init(this, relaxed = true)
        every { journeyHandleActionBuilder.build() } returns journeyHandleAction
        presenter = {Feature}Presenter(journeyHandleActionBuilder)
        presenter.startModule(module)
    }

    @Test
    fun `onPrimaryAction executes next action`() {
        val mockAction = mockk<MvcAction>(relaxed = true)
        every { module.getAction(ActionType.NEXT) } returns mockAction

        presenter.onPrimaryAction(mockk())

        verify { journeyHandleAction.executeAction(mockAction, any(), any()) }
    }
}
```

### 11.3 Testing FlavorDetails branching

```kotlin
@MockK lateinit var flavorDetails: FlavorDetails

// Test Barclays flavor behaviour
every { flavorDetails.isBarclaycard } returns false
viewModel = {Feature}ViewModel(flavorDetails = flavorDetails)
assertEquals("Welcome to Barclays", viewModel.getWelcomeMessage())

// Test Barclaycard flavor behaviour
every { flavorDetails.isBarclaycard } returns true
viewModel = {Feature}ViewModel(flavorDetails = flavorDetails)
assertEquals("Welcome to Barclaycard", viewModel.getWelcomeMessage())
```

---

## 12. TBA Iron Rules (in addition to the android skill Iron Rules)

Apply these on top of the 17 Iron Rules from the base `android` skill:

18. **Extend `BarclaysActivity`** — Activity entry points in BMB ALWAYS extend `BarclaysActivity`, never `AppCompatActivity` directly
19. **No `Scope.get(...)` inside `@Composable`** — resolve all scope dependencies in factories or presenters
20. **No `BuildConfig.FLAVOR` checks in feature code** — ALWAYS use `FlavorDetails` from `CoreScope`
21. **`ActionType` constants for all MVC action IDs** — NEVER hardcode action ID strings
22. **`JourneyFrameworkGenericHandleAction.Builder` created from Activity** — NEVER from inside a Composable or ViewModel
23. **No Activity reference stored in ViewModel** — pass to builders at point-of-use only; holding an Activity in a ViewModel causes memory leaks
24. **`mapIcon()` always has a fallback** — `mapIcon(...) ?: rememberVectorPainter(BlueprintVectors.Outlined.Placeholder)`
25. **Analytics `logScreenView` in `onResume`** — NOT in `onCreate` (to capture re-entries)
