# MCA1-to-MCA2 Migration Runbook

Step-by-step guide to execute a smooth migration from MCA1 JMVC to MCA2 React.

Last Updated: March 25, 2026

---

## Pre-Migration Phase (1-2 weeks)

### Step 1: Team Preparation
**Objective**: Ensure team has necessary knowledge and tools

- [ ] Team trained on React + Redux Toolkit basics
- [ ] Team familiar with Blueprint-React components
- [ ] Team has MCA2 development environment setup
- [ ] IDE configured with TypeScript support
- [ ] Git workflow documented and understood
- [ ] Code review process established

**Checklist**:
```bash
# Verify setup
npm --version        # Node.js installed
node --version       # Correct version
eagle --version      # MCA2 CLI available
npm test -- --version  # Jest working
```

### Step 2: MCA1 Analysis
**Objective**: Understand source application structure

- [ ] Map all controllers (count: _____)
- [ ] Identify all API endpoints (count: _____)
- [ ] Document all BDL components used
- [ ] List all validation rules
- [ ] Identify complex workflows
- [ ] Document state management patterns
- [ ] Create component inventory spreadsheet

**Output**: MCA1_ANALYSIS.md documenting:
- Controllers and their purpose
- API endpoints with request/response formats
- UI components and their layouts
- Validation rules and error messages
- Complex workflows to migrate

### Step 3: Architecture Review
**Objective**: Design MCA2 architecture based on MCA1 analysis

- [ ] Design Redux store structure (see REDUX_PATTERNS.md)
- [ ] Plan component hierarchy
- [ ] Design API service layer
- [ ] Plan form validation approach (Yup + Formik/RHF)
- [ ] Design routing structure (MemoryRouter)
- [ ] Create architecture diagram

**Output**: MCA2_ARCHITECTURE.md including:
- Redux state structure
- Component folder structure
- API service design
- Form validation strategy
- Routing map

---

## Setup Phase (3-5 days)

### Step 4: Create MCA2 Application
**Objective**: Bootstrap new MCA2 React application

```bash
cd mca2
eagle create mca-ui-maintain-roles
cd mca-ui-maintain-roles
npm install
npm run build
```

- [ ] Application created successfully
- [ ] Build runs with 0 errors
- [ ] Development server starts
- [ ] Can access http://localhost:3000

### Step 5: Setup Infrastructure
**Objective**: Configure Redux, API, and foundation

- [ ] Setup Redux store (src/store/)
- [ ] Create Redux slices for roles/services/parameters
- [ ] Create API service layer (src/api/)
- [ ] Define TypeScript types (src/types/)
- [ ] Setup API interceptors
- [ ] Configure Yup validation schemas
- [ ] Setup routing structure

**Files to Create**:
```
src/
  store/
    index.ts
    slices/
      rolesSlice.ts
      servicesSlice.ts
      parametersSlice.ts
  api/
    endpoints.ts
    services.ts
    interceptors.ts
  types/
    index.ts
  validation/
    schemas.ts
  hooks/
    useNavigation.ts
  routes/
    AppRoutes.tsx
```

### Step 6: Create Base Components
**Objective**: Build reusable UI components

- [ ] ActionButton (wrapper for Button)
- [ ] MessageAlert (for success/error messages)
- [ ] MainLayout (page layout wrapper)
- [ ] FormField (wrapper for form inputs)
- [ ] ConfirmDialog (confirmation dialogs)

**Reference**: BLUEPRINT_REACT_CORRECT_PATTERNS.md

### Step 7: Test Infrastructure
**Objective**: Verify infrastructure is working

```bash
# Test Redux
npm test -- rolesSlice.test.ts

# Test API
npm test -- services.test.ts

# Test components
npm test -- ActionButton.test.ts

# Full build
npm run build

# Check coverage
npm test -- --coverage
```

---

## Development Phase (2-3 weeks)

### Step 8: Feature Migration (Parallel Streams)

#### Stream A: Roles Feature
**Timeline**: 4-5 days

- [ ] Dashboard page component
- [ ] Add Role dialog
- [ ] Edit Role dialog
- [ ] Delete Role confirmation
- [ ] Role list with actions
- [ ] Roles Redux slice (fully complete)
- [ ] Roles API services
- [ ] Roles validation schemas
- [ ] Unit tests for roles
- [ ] Component tests for role dialogs

**Checklist before moving to next stream**:
- [ ] Build passes with 0 errors
- [ ] All tests passing
- [ ] Component audit checklist complete
- [ ] Redux state verified in DevTools

#### Stream B: Services Feature
**Timeline**: 4-5 days

- [ ] Services list page
- [ ] Add Service dialog
- [ ] Service-to-Roles assignment
- [ ] Services Redux slice
- [ ] Services API services
- [ ] Services validation
- [ ] Unit & component tests

#### Stream C: Parameters Feature
**Timeline**: 3-4 days

- [ ] Parameters list page
- [ ] Add Parameter dialog
- [ ] Parameter management
- [ ] Parameters Redux slice
- [ ] Parameters API services
- [ ] Unit & component tests

### Step 9: Cross-Feature Integration
**Timeline**: 2-3 days

- [ ] Roles with Services relationship
- [ ] Roles with Parameters relationship
- [ ] Service-to-Roles bulk operations
- [ ] Parameter-to-Roles assignments
- [ ] Integration tests for workflows

### Step 10: Error Handling & Edge Cases
**Timeline**: 2-3 days

- [ ] 401/403 authentication errors
- [ ] 404 not found errors
- [ ] 400 validation errors
- [ ] Network timeouts
- [ ] Empty state handling
- [ ] Loading state UI
- [ ] Error boundaries

**Reference**: ERROR_SCENARIOS.md, DEBUGGING_GUIDE.md

### Step 11: Performance & Optimization
**Timeline**: 1-2 days

- [ ] Redux selector memoization
- [ ] React.memo for expensive components
- [ ] useCallback for event handlers
- [ ] Lazy loading for routes
- [ ] Code splitting analysis

**Reference**: PERFORMANCE_OPTIMIZATION_GUIDE.md

---

## Testing Phase (3-5 days)

### Step 12: Unit & Integration Testing
**Objective**: Achieve 80%+ code coverage

```bash
# Run all tests
npm test -- --coverage

# Target coverage
Statements: 80%+
Branches: 80%+
Functions: 80%+
Lines: 80%+
```

- [ ] Unit tests for all reducers
- [ ] Unit tests for all async thunks
- [ ] Unit tests for all components
- [ ] Integration tests for workflows
- [ ] Form submission tests
- [ ] Error scenario tests

**Reference**: TESTING_PATTERNS.md

### Step 13: E2E Testing
**Objective**: Test complete user workflows

```bash
# Run E2E tests
npm run cypress:run

# Or interactive
npm run cypress:open
```

- [ ] Role creation workflow
- [ ] Role editing workflow
- [ ] Service assignment to role
- [ ] Parameter assignment to role
- [ ] Error handling scenarios
- [ ] Permission scenarios (if applicable)

**Reference**: TESTING_PATTERNS.md - E2E Testing section

### Step 14: Code Review
**Objective**: Ensure quality and pattern adherence

- [ ] Use COMPONENT_AUDIT_CHECKLIST.md for component review
- [ ] Verify all Mistakes 1-23 are avoided
- [ ] Check Redux patterns (REDUX_PATTERNS.md)
- [ ] Verify API response validation (API_RESPONSE_PATTERNS.md)
- [ ] Validate form patterns (FORM_VALIDATION_PATTERNS.md)
- [ ] Check code coverage

**Code Review Checklist**: CODE_REVIEW_CHECKLIST.md

### Step 15: User Acceptance Testing
**Objective**: Get stakeholder approval

- [ ] Feature parity with MCA1 verified
- [ ] All workflows tested by QA
- [ ] Performance meets expectations
- [ ] Error messages are user-friendly
- [ ] Stakeholder sign-off obtained

---

## Deployment Phase (1-2 days)

### Step 16: Build & Package
**Objective**: Create production build

```bash
# Production build
npm run build:prod

# Verify build size
du -sh dist/

# Create deployment package
npm run package
```

- [ ] Production build succeeds
- [ ] Bundle size acceptable
- [ ] Source maps generated
- [ ] Deployment artifact ready

### Step 17: Staging Deployment
**Objective**: Test in staging environment

- [ ] Deploy to staging
- [ ] Verify all endpoints accessible
- [ ] Test with staging data
- [ ] Verify API integration
- [ ] Performance testing
- [ ] Security testing

### Step 18: Documentation
**Objective**: Document deployment and operations

- [ ] Create deployment guide
- [ ] Document troubleshooting procedures
- [ ] Create runbook for common issues
- [ ] Document rollback procedure
- [ ] Update team wiki/documentation

### Step 19: Production Deployment
**Objective**: Release to production

**Deployment Checklist**:
- [ ] Backup current MCA1 version
- [ ] Feature flag in place (optional)
- [ ] Monitoring/logging enabled
- [ ] Team on standby
- [ ] Rollback plan ready
- [ ] Deployment executed
- [ ] Smoke tests passed
- [ ] Team monitoring production

**Monitoring**:
- [ ] Error rates normal
- [ ] API response times normal
- [ ] No unusual resource usage
- [ ] User feedback positive

---

## Post-Migration Phase (1 week)

### Step 20: Monitoring & Fixes
**Objective**: Support production operation

- [ ] Monitor error logs
- [ ] Fix critical issues immediately
- [ ] Gather user feedback
- [ ] Document learnings
- [ ] Address edge cases discovered

### Step 21: Decommission MCA1
**Objective**: Retire old application

- [ ] Confirm all users on MCA2
- [ ] No requests to MCA1 endpoints
- [ ] Archive MCA1 codebase
- [ ] Remove MCA1 from production
- [ ] Cleanup temporary infrastructure

### Step 22: Knowledge Transfer
**Objective**: Document for future maintenance

- [ ] Update team documentation
- [ ] Conduct team retrospective
- [ ] Identify lessons learned
- [ ] Update migration skill with findings
- [ ] Create maintenance guide

---

## Risk Mitigation

### Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| API incompatibility | Medium | High | API analysis & adapter layer |
| Performance issues | Medium | High | Early performance testing |
| Data inconsistency | Low | High | Comprehensive testing |
| Team skill gap | Medium | Medium | Training & pairing |
| Timeline overrun | Medium | Medium | Buffer & parallel work |
| Rollback needed | Low | Critical | Rollback plan in place |

### Rollback Plan

```
If critical issues discovered:

1. Switch traffic back to MCA1 (feature flag or load balancer)
2. Investigate issue in MCA2
3. Fix and redeploy OR wait 24-48 hours
4. Plan retry deployment
5. Post-mortem with team
```

---

## Success Criteria

**Technical Success**:
- ✅ 0 TypeScript errors
- ✅ Build passes all checks
- ✅ 80%+ test coverage
- ✅ All E2E tests passing
- ✅ Performance meets SLA
- ✅ All API endpoints working

**Functional Success**:
- ✅ Feature parity with MCA1
- ✅ All validation rules working
- ✅ Error handling complete
- ✅ Workflows match MCA1
- ✅ UI/UX matches design
- ✅ Stakeholder approved

**Operational Success**:
- ✅ Deployed to production
- ✅ Monitoring in place
- ✅ Team trained
- ✅ Documentation complete
- ✅ No critical issues in first week
- ✅ MCA1 decommissioned

---

## Timeline Summary

| Phase | Duration | Tasks |
|-------|----------|-------|
| Pre-Migration | 1-2 weeks | Analysis, training, planning |
| Setup | 3-5 days | Infrastructure, base components |
| Development | 2-3 weeks | Feature development (parallel) |
| Testing | 3-5 days | Unit, integration, E2E tests |
| Deployment | 1-2 days | Build, staging, production |
| Post-Migration | 1 week | Monitoring, fixes, decommissioning |
| **Total** | **4-5 weeks** | Complete migration |

---

## References
- COMPONENT_AUDIT_CHECKLIST.md
- CODE_REVIEW_CHECKLIST.md
- TESTING_PATTERNS.md
- ERROR_SCENARIOS.md
- DEBUGGING_GUIDE.md
- SKILL.md Mistakes 1-23
