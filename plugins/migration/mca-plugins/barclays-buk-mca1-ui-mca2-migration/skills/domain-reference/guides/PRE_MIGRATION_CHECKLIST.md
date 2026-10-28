# Pre-Migration Checklist

Complete this checklist before starting MCA1-to-MCA2 migration.

Last Updated: March 25, 2026

---

## Team Preparation (1-2 weeks before)

### Knowledge & Skills
- [ ] Team trained on React fundamentals
- [ ] Team trained on Redux Toolkit basics
- [ ] Team familiar with Blueprint-React component library
- [ ] Team understands MCA2 framework architecture
- [ ] Team has hands-on experience with TypeScript
- [ ] Team familiar with Jest/React Testing Library
- [ ] At least one team member knows Cypress for E2E testing
- [ ] Team understands BDL-to-Blueprint component mapping

**Training Resources**:
- React: https://react.dev/learn
- Redux: https://redux.js.org/tutorials/essentials/part-1-overview-and-concepts
- TypeScript: https://www.typescriptlang.org/docs/
- Jest: https://jestjs.io/docs/getting-started
- Blueprint-React: BLUEPRINT_REACT_REFERENCE.md

### Tools & Environment
- [ ] All team members have Node.js 16+ installed
- [ ] npm/yarn properly configured
- [ ] Git configured for team
- [ ] IDE has TypeScript support enabled
- [ ] ESLint extension installed
- [ ] Prettier extension installed
- [ ] Redux DevTools browser extension installed
- [ ] React DevTools browser extension installed

**Setup Verification**:
```bash
node --version          # Should be 16+
npm --version           # Should be 8+
git --version           # Should be available
echo $PATH | grep npm   # npm should be in PATH
```

### Communication & Planning
- [ ] Migration sponsor identified
- [ ] Migration team leads identified
- [ ] Stakeholder expectations set
- [ ] Timeline communicated
- [ ] Rollback plan discussed
- [ ] Team meetings scheduled
- [ ] Code review process defined

---

## MCA1 Application Analysis (1 week)

### Feature & Workflow Inventory
- [ ] Total number of controllers: _____
- [ ] Total number of EJS view templates: _____
- [ ] Total number of BDL components used: _____
- [ ] Total API endpoints: _____
- [ ] Main features identified: _____
- [ ] Complex workflows documented: _____
- [ ] User roles/permissions mapped: _____

### API Endpoint Documentation
**Create spreadsheet with columns**:
- Endpoint name
- HTTP method (GET, POST, PUT, DELETE)
- Request parameters
- Response format
- Error codes
- Authentication required (Y/N)
- Used by which views

**Count**: Total endpoints = _____ (Target: 100% mapping)

### Validation Rules Extraction
- [ ] Identify all validation in model.js files
- [ ] Document validation rules with error messages
- [ ] Categorize: field-level vs form-level
- [ ] Note dependencies between fields
- [ ] Note async validations (uniqueness checks)

**Template**:
```
Field: role_name
Type: String
Rules:
  - Required
  - Min length: 3
  - Max length: 50
  - Pattern: ^[a-zA-Z0-9_-]+$
Error Messages:
  - "Role name is required"
  - "Role name must be at least 3 characters"
```

### BDL Component Usage
- [ ] Identify all BDL components used
- [ ] Document each component's usage
- [ ] Check BDL_TO_BLUEPRINT_REACT.md for mapping
- [ ] Identify missing equivalents
- [ ] Plan custom components for missing features

**Template**:
```
BDL Component: bdl-button
Used in: maintainroles.ejs (lines 45, 67, 89)
Attributes: label, icon, click handler
Blueprint Equivalent: Button
Mapping: direct
```

### State Management Analysis
- [ ] Document how workflow.model() is used
- [ ] Identify all state variables
- [ ] Note dependencies between states
- [ ] Plan Redux slice structure
- [ ] Identify normalized vs denormalized data

---

## MCA1 Documentation (3-5 days)

### Create MCA1_ANALYSIS.md
Document:
- [ ] Controllers and their responsibilities
- [ ] API endpoints with full specifications
- [ ] BDL components and their usage
- [ ] Validation rules with error messages
- [ ] State management patterns
- [ ] User workflows
- [ ] Navigation flows
- [ ] Known issues or edge cases

### Create Wireframes/Component Map
- [ ] Screenshot each MCA1 page
- [ ] Annotate with component names
- [ ] Note layout structure
- [ ] Document form fields
- [ ] List buttons and actions

### Create Test Scenario Document
- [ ] Happy path scenarios
- [ ] Error scenarios
- [ ] Edge cases
- [ ] Permission scenarios (if applicable)
- [ ] Performance considerations

---

## Architecture Planning (3-5 days)

### Redux Store Design
- [ ] Design state structure
- [ ] Identify slices needed
- [ ] Plan normalization strategy
- [ ] Document relationships
- [ ] Plan loading/error states

**Template**:
```typescript
{
  roles: {
    byId: { [id]: Role },
    allIds: string[],
    selectedId: string | null,
    loading: boolean,
    error: string | null
  },
  services: { /* ... */ },
  parameters: { /* ... */ },
  ui: {
    modals: { /* ... */ },
    messages: { /* ... */ }
  }
}
```

### Component Hierarchy
- [ ] Design component tree
- [ ] Identify page/route components
- [ ] Identify dialog components
- [ ] Identify form components
- [ ] Identify reusable components

**Template**:
```
App
├── Dashboard (page)
│   ├── RoleSection
│   │   ├── RoleSelect
│   │   ├── RoleActionSelect
│   │   └── RoleButtons
│   ├── ServiceSection
│   │   ├── ServiceSelect
│   │   └── ServiceButtons
│   └── ParameterSection
├── AddRoleDialog (modal)
│   └── AddRoleForm
├── EditRoleDialog (modal)
│   └── EditRoleForm
└── Navigation
```

### API Service Layer Design
- [ ] Document API client structure
- [ ] Plan interceptor strategy
- [ ] Design error handling
- [ ] Plan retry logic
- [ ] Plan request/response transformation

### Form & Validation Strategy
- [ ] Identify all forms
- [ ] Plan validation approach (Yup + Formik/RHF)
- [ ] Design validation schemas
- [ ] Plan error display strategy
- [ ] Plan async validation approach

### Routing Strategy
- [ ] Design route structure
- [ ] Plan MemoryRouter setup (not BrowserRouter!)
- [ ] Document route transitions
- [ ] Plan navigation hooks
- [ ] Design breadcrumb strategy

---

## Environment Setup (2-3 days)

### Development Environment
- [ ] Clone MCA2 skeleton/template
- [ ] Create new application: `eagle create mca-ui-maintain-roles`
- [ ] Install dependencies: `npm install`
- [ ] Verify build: `npm run build`
- [ ] Verify dev server: `npm start`
- [ ] Verify tests: `npm test`

### Git Repository Setup
- [ ] Repository created
- [ ] Branch protection rules set
- [ ] Code review requirements configured
- [ ] CI/CD pipeline configured
- [ ] Pre-commit hooks configured (if needed)

### Build & CI/CD Setup
- [ ] Build script configured
- [ ] Test script configured
- [ ] Lint script configured
- [ ] Coverage reporting configured
- [ ] CI pipeline configured (GitHub Actions, GitLab CI, etc.)

---

## Documentation Preparation (3-5 days)

### Reference Files Review
- [ ] Read SKILL.md (understand all 23 Mistakes)
- [ ] Review BLUEPRINT_REACT_CORRECT_PATTERNS.md
- [ ] Review BDL_TO_BLUEPRINT_REACT.md (includes icon mapping in Section 8)
- [ ] Review BDL_TO_BLUEPRINT_REACT.md
- [ ] Bookmark REDUX_PATTERNS.md
- [ ] Bookmark API_RESPONSE_PATTERNS.md
- [ ] Bookmark FORM_VALIDATION_PATTERNS.md
- [ ] Bookmark TESTING_PATTERNS.md
- [ ] Review ERROR_SCENARIOS.md
- [ ] Review DEBUGGING_GUIDE.md

### Create Team Wiki
- [ ] Create migration project page
- [ ] Link all reference documents
- [ ] Create FAQ section
- [ ] Create troubleshooting section
- [ ] Create decision log

### Setup Documentation Links
Create quick reference cheat sheet with links to:
- COMPONENT_AUDIT_CHECKLIST.md
- CODE_REVIEW_CHECKLIST.md
- MIGRATION_RUNBOOK.md
- Common mistakes by topic
- Error scenarios by error type

---

## Risk Assessment (2-3 days)

### Identify Risks
- [ ] Technical risks assessed
- [ ] Schedule risks assessed
- [ ] Resource risks assessed
- [ ] Knowledge/skill risks assessed
- [ ] Communication risks assessed

### Risk Mitigation Plan
For each identified risk:
- [ ] Mitigation strategy documented
- [ ] Responsible person assigned
- [ ] Timeline defined
- [ ] Success criteria defined

**Template**:
```
Risk: API incompatibility
Probability: Medium
Impact: High
Mitigation:
  - Comprehensive API analysis completed (3 days)
  - Create API compatibility layer if needed (5 days)
  - Test all endpoints thoroughly (3 days)
Responsible: [Name]
Timeline: Week 1-2
```

### Rollback Plan
- [ ] Rollback procedure documented
- [ ] Rollback timeline defined (target: < 30 minutes)
- [ ] Rollback tested (if possible)
- [ ] Communication plan for rollback
- [ ] Stakeholder approval obtained

---

## Stakeholder Alignment (1-2 days)

### Requirements Confirmation
- [ ] Feature parity requirements confirmed
- [ ] Performance requirements confirmed
- [ ] Timeline confirmed
- [ ] Resource availability confirmed
- [ ] Go-live date confirmed

### Communication Plan
- [ ] Weekly status update schedule defined
- [ ] Stakeholder contact list prepared
- [ ] Escalation process defined
- [ ] Status report template created

### Success Criteria Alignment
**Technical**:
- [ ] Build succeeds with 0 errors
- [ ] 80%+ test coverage
- [ ] All E2E tests pass
- [ ] Performance benchmark met

**Functional**:
- [ ] Feature parity achieved
- [ ] All workflows work
- [ ] Stakeholder testing completed
- [ ] Sign-off obtained

---

## Final Readiness Assessment

### Team Readiness
- [ ] All team members trained ✓
- [ ] All team members have environment setup ✓
- [ ] Roles and responsibilities assigned ✓
- [ ] Team has access to all documentation ✓
- [ ] Team has experience with example migration ✓

### Infrastructure Readiness
- [ ] Development environment ready ✓
- [ ] Testing environment available ✓
- [ ] Staging environment available ✓
- [ ] CI/CD pipeline working ✓
- [ ] Git repository ready ✓

### Documentation Readiness
- [ ] MCA1 analysis completed ✓
- [ ] Architecture designed ✓
- [ ] Component map created ✓
- [ ] Test scenarios prepared ✓
- [ ] Risk mitigation plan ready ✓

### Stakeholder Readiness
- [ ] Requirements confirmed ✓
- [ ] Timeline agreed ✓
- [ ] Success criteria defined ✓
- [ ] Communication plan ready ✓
- [ ] Approval obtained ✓

---

## Go/No-Go Decision

**Proceed if ALL items checked** ✓

### Sign-Off

Team Lead: _____________ Date: _________

Stakeholder: _____________ Date: _________

Project Manager: _____________ Date: _________

---

## References
- MIGRATION_RUNBOOK.md - Detailed execution guide
- SKILL.md - Common mistakes to avoid
- COMPONENT_AUDIT_CHECKLIST.md - Component review
- CODE_REVIEW_CHECKLIST.md - Code review standards
- ERROR_SCENARIOS.md - Expected issues and fixes
- DEBUGGING_GUIDE.md - Troubleshooting guide
