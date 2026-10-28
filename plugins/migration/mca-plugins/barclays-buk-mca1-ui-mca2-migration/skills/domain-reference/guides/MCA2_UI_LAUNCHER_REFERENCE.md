# MCA2 UI Launcher and Core Reference

## Overview
**Repository**: mca-ui-core (Monorepo with Lerna)
**Version**: 0.0.0
**Build System**: Lerna + Eagle Scripts
**Package Count**: 39 packages
**Framework**: React 19.2.4 + TypeScript
**Module Bundler**: Webpack 5.72.0

## Repository Structure

### Root Configuration
```
mca-ui-core/
├── lerna.json              # Lerna monorepo config (fixed mode)
├── package.json            # Root dependencies
├── package-lock.json       # Lock file (respected at root only)
├── packages/               # Individual packages
├── container/              # Example apps in container
├── scripts/                # Build and utility scripts
└── .gitlab-ci.yml          # CI/CD pipeline
```

### Lerna Monorepo Setup

**Mode**: Fixed version (all packages share same version)

**Key Commands**:
```bash
lerna run test --stream            # Run tests across all packages
lerna run build --stream           # Build all packages
lerna publish --registry <url>     # Publish to Nexus (Jenkins only)
```

**Dependency Hoisting**:
- All `devDependencies` hoisted to root
- Packages use Node module resolution chain
- Symlinks or copies created in package `node_modules/.bin`
- Reduces installation time and ensures version consistency

## Core Packages

### API Packages (packages/api-*)

#### api-mca-launcher
- **Purpose**: Core launcher for starting MCA instances
- **Main Export**: `AppLauncher`, `Launcher` class
- **Dependencies**:
  - @barclays/mca-api-mca
  - @barclays/mca-lib-blueprint-flow
  - @barclays/mca-lib-fetch
  - @barclays/mca-session-timeout
  - @barclays/mca-api-timeout

```typescript
export { AppLauncher } from './lib/support/app-launcher';
export * from './lib/support/libraryConfigurators/default-api-mca-library-configurator';
export * from './lib/support/child-process-launching-flow-service';
export * from './lib/support/default-mca-display-strategy';
export * from './lib/support/dynamic-target-element-provider';
export * from './lib/support/fallback-bootstrap-context-provider';
export * from './lib/support/inline-script-module-loader';
export * from './lib/support/instance-module-loader';
export * from './lib/support/bootstrapContextProvider/remote-bootstrap-context-provider';
export * from './lib/support/libraryConfigurators/static-api-mca-library-configurator';
export * from './lib/support/bootstrapContextProvider/static-bootstrap-context-provider';
export * from './lib/support/static-target-element-provider';
export * from './lib/support/static-target-element-provider';
export * from './lib/interfaces/api-mca-library-configurator';
export * from './lib/interfaces/bootstrap-context-provider';
export * from './lib/interfaces/bootstrap-context';
export * from './lib/interfaces/launcher-context';
export * from './lib/interfaces/mca-display-strategy';
export * from './lib/interfaces/module-loader';
export * from './lib/interfaces/target-element-provider';
export * from './lib/launcher';
export * from './lib/interfaces/lifeCycleHandler/apiMCAReference';
export * from './lib/interfaces/lifeCycleHandler/lifeCycleHandler';
```

**Usage**:
```typescript
import { AppLauncher } from '@barclays/mca-api-mca-launcher';

const launcher = new AppLauncher();
launcher.launch({ ...options });
```

#### api-mca-launcher-bcard-full
- **Purpose**: Full launcher for Business Card (bcard) channel

#### api-mca-launcher-bmb-full
- **Purpose**: Full launcher for Barclays Mobile Banking (bmb) channel

#### api-mca-launcher-rolb-full
- **Purpose**: Full launcher for ROLB (Rest of Life Banking) channel

#### api-mca
- **Purpose**: Main MCA API entry point
- **Exports**: Core MCA framework
- **Dependencies**:
  - @barclays/mca-api-communication
  - @barclays/mca-api-flow
  - @barclays/mca-api-logger
  - @barclays/mca-api-service
  - @barclays/mca-data-collector

#### api-communication
- Communication protocols and APIs
- Used by all other packages

#### api-flow
- Flow/workflow management
- State machine support

#### api-logger
- Logging abstraction
- Multiple logger implementations

#### api-service
- Service definition and discovery
- Service lifecycle management

#### api-timeout
- Session timeout handling
- Timeout configuration

#### api-validation
- Data validation utilities
- Schema validation support

### Library Packages (packages/lib-*)

#### lib-angular-core-api
- Angular integration support
- Bridges to MCA core

#### lib-adobe-tagging
- Adobe Analytics integration
- Event tracking

#### lib-blueprint
- Blueprint design system integration
- Component wrappers

#### lib-blueprint-flow
- Flow components for Blueprint
- Workflow UI components

#### lib-bridge
- Bridge communication protocol
- IFrame/Window bridge implementation

#### lib-bridge-communication
- Bridge message handling
- Protocol implementation details

#### lib-broadcast-channel-communication
- BroadcastChannel API integration
- Cross-tab communication

#### lib-channel-message-communication
- Message channel communication
- PostMessage API integration

#### lib-data-adapter
- Data adaptation layer
- Transform data between formats

#### lib-data-collector
- Data collection utilities
- Analytics data gathering

#### lib-fetch
- Fetch API abstraction
- Request/response interceptors

```typescript
export * from '@barclays/mca-lib-fetch/lib/interceptors';
```

#### lib-jsonlog-logger
- JSON structured logging
- Log aggregation support

#### lib-react-context-provider
- React Context setup
- Provider component utilities

#### lib-react-error-handler
- Error boundary implementation
- Error handling strategies

#### lib-session-timeout
- Session timeout management
- User inactivity handling

#### lib-utilities
- General utility functions
- Helper functions

#### lib-validations
- Validation rule libraries
- Reusable validators

## Monorepo Workflows

### Fresh Installation

```bash
# Clean installation
npx lerna clean --yes && rm -rf node_modules

# Install from root
npm install && npm run bootstrap

# Windows-specific
npm run bootstrap:windows
```

### Adding Dependencies

**Adding devDependency**:
1. Add to root `package.json` devDependencies
2. Run `npm install` at root

**Adding package dependency**:
1. Add to package's `package.json` dependencies
2. Run `npm install packages/package-name` at root

### Running Commands Across Packages

```bash
lerna run build --stream           # Run build in all packages
lerna run test --stream            # Run tests
lerna run lint --stream            # Run linting
```

## Build Configuration

### Each Package Requires

**package.json scripts**:
```json
{
  "scripts": {
    "build": "eagle build",
    "docs": "eagle docs",
    "test": "eagle test",
    "lint": "eagle lint",
    "dts": "eagle dts"
  },
  "devDependencies": {
    "@barclays/mca-build-core": "0.2.41"
  }
}
```

### Eagle Scripts Integration

All packages use Eagle Framework (mca-eagle-scripts) for:
- Webpack configuration
- Jest testing
- ESLint linting
- TypeScript compilation
- Build optimization

## Lifecycle Handler

### API MCA Reference
Provides reference to running MCA instances:
```typescript
export interface ApiMCAReference {
  // Instance methods and properties
}
```

### Life Cycle Handler
Manages MCA lifecycle:
```typescript
export interface LifeCycleHandler {
  onInit(): void;
  onLoad(): void;
  onStart(): void;
  onStop(): void;
}
```

## Fetch Interceptors

Request/response interceptor utilities:
```typescript
export * from '@barclays/mca-lib-fetch/lib/interceptors';
```

## NPM Scripts

### Root Level
```bash
npm run bootstrap        # Setup for development
npm run bootstrap:windows # Windows-specific setup
npm run lint            # Lint all packages
npm run test            # Test all packages
npm run test:dev        # Test in watch mode
npm run build           # Build all packages
npm run build:only      # Build without lint/test
npm run analyze         # Bundle size analysis
npm run docs            # Generate documentation
npm run dts             # Generate type definitions
npm run clean           # Clean all packages
npm run remove-dist     # Remove dist folders
npm run symlink-bins    # Create bin symlinks
npm run lerna-publish   # Publish to Nexus
npm run commit          # Commit with proper format
```

## Key Technologies

### Build and Module System
- **Lerna**: 6.6.2 - Monorepo management
- **Webpack**: 5.72.0 - Bundling
- **TypeScript**: 5.8.3 - Type safety
- **Babel**: 7.27.2 - Transpilation

### Testing
- **Jest**: 29.7.0 - Unit testing
- **React Testing Library**: 14.0.0 - Component testing
- **Stryker**: 8.7.1 - Mutation testing

### React and State
- **React**: 19.2.4
- **React DOM**: 19.2.4
- **Redux**: 4.1.0
- **Redux Thunk**: 2.3.0

### Development
- **TypeScript**: 5.8.3
- **ESLint**: 7.30.0
- **Node**: 14.14.31+

## Configuration Files

### lerna.json
```json
{
  "packages": ["packages/*"],
  "version": "independent"
}
```

### Root package.json
- All devDependencies hoisted
- Overrides for transitive dependencies
- Package auto-changelog support

## Nexus Repository Integration

### Configuration
Registry in root package.json:
```json
{
  "publishConfig": {
    "registry": "https://barcorpnexus.barcapint.com:8443/nexus/content/repositories/npm_mca"
  }
}
```

### Publishing
- Only via Jenkins pipeline (lerna publish command)
- Automatic version management
- Dependency resolution from Nexus

## Windows-Specific Configuration

### Symlink Support
Some Windows versions don't support symlinks:
```bash
npm run bootstrap:windows
```

This copies instead of symlinks and sets up proper module resolution.

### Git Bash for Scripts
Configure for Windows:
```bash
npm config set script-shell "C:\\Program Files\\git\\bin\\bash.exe"
```
