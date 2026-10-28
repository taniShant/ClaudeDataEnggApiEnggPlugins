# SCP Foundation Libraries Reference

## Overview
**Repository**: scp-libs-ui-foundation
**Build System**: Gradle
**Technology Stack**: Java/Groovy with JavaScript frontend
**Version**: 24.11
**Purpose**: Provides base UI components, styles, and utilities for SCP applications

## Project Structure

```
src/main/webapp/scp/maintainroles/manageroles/
├── controllers/      # JMVC Controllers
├── models/          # Data models
├── views/           # EJS view templates
├── constants/       # Application constants
├── styles/          # SASS/CSS styling
├── tests/           # Unit/functional tests
└── scripts/         # Build scripts
```

## Core Architecture Components

### 1. MVC Framework: JavaScriptMVC (JMVC)

**Framework Version**: JavaScriptMVC 3.2.2
**Module Loader**: Steal.js
**View Engine**: EJS (Embedded JavaScript)

```javascript
steal(function($) {
  scp.maintainroles.manageroles.controllers.MaintainRolesBaseController(
    'scp.maintainroles.manageroles.controllers.maintainroles', {
      init: function() {
        this._super.apply(this, arguments);
        this.loadRoles();
      },
      loadRoles: function() {
        this.callService('service', 'fetch-all-roles', {})
          .done(this.proxy(this.populateRoles))
          .fail(this.proxy(this.showError));
      }
    }
  );
});
```

### 2. Base Controller Pattern

**Location**: `src/main/webapp/scp/maintainroles/manageroles/controllers/base.js`

Extends `scp.ui.common.controllers.BaseController` with:

- **Message Handling**: Success/error notifications
- **Window Management**: Dialog and window lifecycle
- **Event Handling**: Event proxying and delegation
- **State Management**: Workflow model management

```javascript
class MaintainRolesBaseController extends BaseController {
  disable() { /* disable UI */ }
  enable() { /* enable UI */ }
  showSuccess(message) { /* show success */ }
  showError(message) { /* show error */ }
}
```

### 3. Service Communication Pattern

All backend calls follow this pattern:

```javascript
this.callService('service-name', 'operation-name', payload)
  .done(this.proxy(onSuccess))
  .fail(this.proxy(onError), this.proxy(onFinally))
  .always(this.proxy(onComplete));
```

Features:
- jQuery Promise-based API
- Automatic UI disable/enable state management
- Error/success message handling
- Request/response transformation

### 4. Workflow Model Pattern

Data flows through workflow system for screen navigation:

```javascript
// Store data for navigation
this.workflow.model('ROLES_DATA', rolesArray);

// Later retrieve in another controller/view
var data = this.workflow.model('ROLES_DATA');
```

### 5. Web Components: BDL (Barclays Design Language)

Specified in controller configuration:

```javascript
{
  webComponents: {
    bundles: ['bdl']  // Includes BDL component bundle
  }
}
```

BDL components are:
- Pre-minified and bundled
- Automatically included in build
- Configured in `build.gradle` minimizations

## Key Configuration Files

### 1. build.gradle
- Project configuration and dependencies
- Gradle task definitions (build, clean, test)
- WAR generation configuration
- Artifact publishing setup

### 2. gradle/version.gradle
- Version management: `project.ext.major` and `project.ext.minor`
- Current: 24.11

### 3. gradle/local_env_scp-config.properties
- Local development configuration
- Copied to `env/container/WEB-INF/classes/scp-config.properties`
- Editable for local customization

### 4. gradle/apaas_war_scp-config.properties
- Production APaaS deployment configuration
- Used for WAR generation

### 5. common.xml
- Ant macros for build process
- JavaScript minification rules
- View file handling

## Main Controllers

### 1. maintainroles.js
- Primary controller for role management interface
- Loads and displays all roles
- Manages service and parameter associations
- Handles role filtering and search

### 2. addrole.js
- Role creation workflow
- Form validation and submission
- Service association during role addition

### 3. deleterole.js
- Role deletion workflow
- Confirmation dialogs
- Cascade deletion handling

### 4. addservice.js
- Service assignment to roles
- Service parameter management
- Bulk operations support

### 5. removeservicefromroles.js
- Service removal from roles
- Confirmation and validation

### 6. addparam.js / maintainparam.js
- Parameter creation and modification
- Parameter binding to services/roles

## Application Constants

**Location**: `src/main/webapp/scp/maintainroles/manageroles/constants/rolesconstants.js`

Defines:
- EJS view file paths
- Operation type constants
- Field name mappings
- UI element IDs

```javascript
const constants = {
  VIEWS: {
    MAINTAIN_ROLES: 'views/maintainroles.ejs',
    ADD_ROLE: 'views/addrole.ejs',
    // ...
  },
  OPERATIONS: {
    CREATE: 'create',
    UPDATE: 'update',
    DELETE: 'delete'
  },
  FIELDS: {
    ROLE_ID: 'roleId',
    ROLE_NAME: 'roleName',
    // ...
  }
};
```

## Build System

### Gradle Tasks

**Environment Setup**:
```bash
./gradlew setupEnv
```
- Downloads container dependencies
- Copies SCP configuration

**Eclipse IDE Setup**:
```bash
./gradlew eclipse
```

**Build Artifacts**:
```bash
./gradlew build
```
- Minimizes JavaScript files
- Creates TAR archive

**WAR Generation**:
```bash
./gradlew clean build
```
- Packages with SCP container
- Full deployable package

### Build Artifact Locations
- **Local dev**: `env/` folder
- **Build output**: `build/` directory
- **WAR file**: Complete deployable package

## Testing Framework

### Cucumber Tests
- **Location**: `Feature/` directory
- **Fixtures**: `Fixture/` directory
- **Runner**: `src/functional/java/com/barclays/cucumber/runner/FluidTestRunner.java`

Example:
```gherkin
Feature: MCA Role Management

@smokeTest
Scenario: User can add a new role
  Given user is logged in
  When user adds a new role "TestRole"
  Then role appears in list
```

## Container Configuration

### Development Environment
- **Container**: scp-container-cgs:5.0.+
- **Configuration**: local_env_scp-config.properties
- **Logs**: `env/container/logs/`

### Production Environment
- **Container**: scp-container-fullserve:7.3.012
- **Configuration**: apaas_war_scp-config.properties

## Dependencies

### UI Foundation
- `scp-libs-uifoundation:24.12.008` - Base components and styles

### Framework
- `javascriptmvc:javascriptmvc:bi3.2.2` - JMVC framework

### Container
- Development: `scp-container-cgs:5.0.+@war`
- Production: `scp-container-fullserve:7.3.012@war`

## Common Development Tasks

### Adding New Role Operation

1. Create controller in `controllers/`
   ```javascript
   steal('scp/maintainroles/manageroles/controllers/base', function() {
     scp.maintainroles.manageroles.controllers.NewOperation = ...
   });
   ```

2. Update constants in `rolesconstants.js`
   ```javascript
   VIEWS: { NEW_OPERATION: 'views/newop.ejs', ... }
   ```

3. Create EJS view template in `views/newop.ejs`

4. Implement service call:
   ```javascript
   this.callService('service', 'operation', data)
     .done(this.proxy(this.onSuccess))
     .fail(this.proxy(this.onError));
   ```

5. Navigate using workflow:
   ```javascript
   this.workflow.model('OPERATION_DATA', data);
   this.navigateTo('NEW_OPERATION');
   ```

### Modifying UI Components

1. Update EJS templates in `views/`
2. BDL web components are pre-bundled
3. Add necessary CSS in `styles/`
4. Follow existing component patterns

### Updating Configuration

1. Edit `gradle/local_env_scp-config.properties`
2. Run `./gradlew envAddScpConfig` to deploy locally
3. Edit `gradle/apaas_war_scp-config.properties` for APaaS

## Debugging

### Browser Developer Tools
- Enable JavaScript console for errors
- Monitor Network tab for API calls
- Use React/Vue DevTools if available

### Container Logs
Location: `env/container/logs/`

### Local Development Debugging
```javascript
console.log('Debug info', variable);
// Use browser debugger for breakpoints
this.disable(); // Disable UI during debug
```

## Key Files Reference

| File | Purpose |
|------|---------|
| build.gradle | Project configuration and tasks |
| common.xml | Build process macros |
| version.gradle | Version management |
| base.js | Common controller functionality |
| rolesconstants.js | App constants and paths |
| *.feature | Cucumber test scenarios |

## NPM Scripts vs Gradle Tasks

| Task | Command |
|------|---------|
| Setup environment | `./gradlew setupEnv` |
| Generate Eclipse files | `./gradlew eclipse` |
| Build | `./gradlew build` |
| Clean build | `./gradlew clean build` |
| Update config | `./gradlew envAddScpConfig` |
| List all tasks | `./gradlew tasks` |
