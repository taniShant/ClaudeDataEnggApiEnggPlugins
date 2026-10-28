# MCA1-to-MCA2 Migration Guides Index

**Complete reference library for smooth MCA1 JMVC/BDL to MCA2 React migrations**

Last Updated: March 25, 2026

---

## 🚀 Quick Start

**New to migration? Start here:**

1. **Read**: [PRE_MIGRATION_CHECKLIST.md](PRE_MIGRATION_CHECKLIST.md) - Prepare your team
2. **Follow**: [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) - Step-by-step execution
3. **Reference**: [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) - Understand Mistakes 1-23
4. **Build**: Use the pattern guides for each feature type

---

## 📚 Documentation Roadmap

### For Project Leads
Start here to plan and execute migration:

| Document | Purpose | Duration |
|----------|---------|----------|
| [PRE_MIGRATION_CHECKLIST.md](PRE_MIGRATION_CHECKLIST.md) | Prepare team, analyze MCA1, plan architecture | 1-2 weeks |
| [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) | Step-by-step migration phases | Reference |
| [CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md) | Quality gate for code reviews | Reference |

### For Developers (During Development)
Reference these guides while building components:

| Document | When to Use | Topics |
|----------|------------|--------|
| [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) | **Always** - Core reference | Mistakes 1-29, critical patterns |
| [MCA1_APPLICATION_PATTERNS.md](MCA1_APPLICATION_PATTERNS.md) | Understanding MCA1 source | BaseController API, workflow.model, callService, EJS, event delegation |
| [JMVC_TO_REACT_PATTERNS.md](JMVC_TO_REACT_PATTERNS.md) | Converting JMVC→React | Line-by-line pattern mapping, complete examples |
| [FOLDER_STRUCTURE.md](FOLDER_STRUCTURE.md) | Setting up project | Directory layout, naming conventions |
| [TYPESCRIPT_PATTERNS.md](TYPESCRIPT_PATTERNS.md) | Writing typed code | Prop interfaces, Redux types, generics |
| [NAVIGATION_PATTERNS.md](NAVIGATION_PATTERNS.md) | Building navigation | MemoryRouter, route guards, params |
| [CONDITIONAL_RENDERING_PATTERNS.md](CONDITIONAL_RENDERING_PATTERNS.md) | Show/hide fields | Conditional logic, dynamic arrays |
| [STYLING_PATTERNS.md](STYLING_PATTERNS.md) | Layout and theming | Grid, Section/SectionItem, responsive |
| [COMPONENT_AUDIT_CHECKLIST.md](COMPONENT_AUDIT_CHECKLIST.md) | Before submitting PR | Pre-submission verification |
| [BLUEPRINT_REACT_CORRECT_PATTERNS.md](BLUEPRINT_REACT_CORRECT_PATTERNS.md) | Building UI components | Form/Dialog/Table/Button patterns |
| [REDUX_PATTERNS.md](REDUX_PATTERNS.md) | Building state management | Redux Toolkit, thunks, selectors |
| [FORM_LAYOUT_PATTERNS.md](FORM_LAYOUT_PATTERNS.md) | Form structure & spacing | Form wrapper, FormSection paddingTop, description prop |
| [MCA2_PAGE_LAYOUT_PATTERNS.md](MCA2_PAGE_LAYOUT_PATTERNS.md) | Page composition & spacing | Section/SectionItem, Grid, button placement, table layout, modals |
| [FORM_VALIDATION_PATTERNS.md](FORM_VALIDATION_PATTERNS.md) | Building forms | Yup, Formik, React Hook Form |
| [API_RESPONSE_PATTERNS.md](API_RESPONSE_PATTERNS.md) | Building API services | Response validation, error handling |
| [TESTING_PATTERNS.md](TESTING_PATTERNS.md) | Writing tests (reference only) | Unit, integration, E2E tests (Cypress & Playwright) |
| [COMPONENT_DECOMPOSITION_PATTERNS.md](COMPONENT_DECOMPOSITION_PATTERNS.md) | Post-migration refactoring | Breaking monolithic pages into sub-components |

### For Legacy jQuery Components
When the MCA1 codebase uses jQuery plugins alongside or instead of `<mca-*>` web components:

| Document | When to Use | Topics |
|----------|------------|--------|
| [LEGACY_AUTOCOMPLETE_MAPPING.md](../mappings/LEGACY_AUTOCOMPLETE_MAPPING.md) | `.scpAutoComplete()` found | Autocomplete → Blueprint Autocomplete |
| [LEGACY_DIALOG_TOOLTIP_MAPPING.md](../mappings/LEGACY_DIALOG_TOOLTIP_MAPPING.md) | `.dialog()`, tooltips | Dialogs/popups/tooltips → Dialog |
| [LEGACY_DROPDOWN_MAPPING.md](../mappings/LEGACY_DROPDOWN_MAPPING.md) | `.chosen()` found | All Chosen variants → FormSelect/Autocomplete |
| [LEGACY_DATATABLE_MAPPING.md](../mappings/LEGACY_DATATABLE_MAPPING.md) | `.scpTable()` found | DataTable variants → Table + Pagination |
| [LEGACY_LABELS_MAPPING.md](../mappings/LEGACY_LABELS_MAPPING.md) | `scp-label`, `scp-readOnlyText` | Labels → Type + FormItem |
| [LEGACY_TYPOGRAPHY_MAPPING.md](../mappings/LEGACY_TYPOGRAPHY_MAPPING.md) | `scp-text`, headings | Typography → Type |
| [LEGACY_ACCORDION_TABS_MAPPING.md](../mappings/LEGACY_ACCORDION_TABS_MAPPING.md) | `.expandable()`, `tab-section` | Accordion/Tabs → Blueprint equivalents |
| [LEGACY_LAYOUT_MAPPING.md](../mappings/LEGACY_LAYOUT_MAPPING.md) | `row`, `*-columns`, separators | Grid/separators/header/footer layout |
| [LEGACY_MISC_MAPPING.md](../mappings/LEGACY_MISC_MAPPING.md) | `scp-message-*`, spinners | Messages/progress/loading/buttons |
| [LEGACY_CALENDAR_CUSTOM_MAPPING.md](../mappings/LEGACY_CALENDAR_CUSTOM_MAPPING.md) | `CalendarUI`, validation | Calendar/selectToRadio/validation |

### For Additional Web Components
Recently added web component mappings:

| Document | When to Use | Topics |
|----------|------------|--------|
| [BDL_FILE_UPLOAD_MAPPING.md](../mappings/BDL_FILE_UPLOAD_MAPPING.md) | `<mca-file-upload>` | DragDrop + SimpleFileUpload |
| [BDL_CALENDAR_MAPPING.md](../mappings/BDL_CALENDAR_MAPPING.md) | `<mca-calendar>` | @barclays/mca-react-calendar |
| [BDL_PROGRESSIVE_MAPPING.md](../mappings/BDL_PROGRESSIVE_MAPPING.md) | `<mca-progressive>` | ProgressVertical + ProgressVerticalItem |
| [BDL_TIME_MAPPING.md](../mappings/BDL_TIME_MAPPING.md) | `<mca-time>` (deprecated) | Redirect to combobox timepicker |
| [BDL_VALIDATION_PATTERNS_MAPPING.md](../mappings/BDL_VALIDATION_PATTERNS_MAPPING.md) | Form validation patterns | Yup + FormItem error + Alert |

### For Troubleshooting
When something goes wrong:

| Document | When to Use | Topics |
|----------|------------|--------|
| [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md) | Investigation tools | Console, Network, Redux DevTools, Memory |
| [ERROR_SCENARIOS.md](ERROR_SCENARIOS.md) | Specific error message | 12 real-world errors with solutions |

---

## 🎯 Documentation by Use Case

### "My migrated component is too large (300+ lines)"
1. Read: COMPONENT_DECOMPOSITION_PATTERNS.md
2. Identify repeated patterns (YesNoRadioGroup, PageLoader)
3. Split into page folder with sub-components
4. Verify: lint, test, build

### "I need to build a new component"
1. Read: BLUEPRINT_REACT_CORRECT_PATTERNS.md
2. Use: COMPONENT_AUDIT_CHECKLIST.md before PR
3. Reference: CODE_REVIEW_CHECKLIST.md for review

### "I need to manage state with Redux"
1. Read: REDUX_PATTERNS.md (section matching your need)
2. Verify: No state duplication (Normalized State Design)
3. Test: TESTING_PATTERNS.md - Testing Async Thunks

### "I need to build a form"
1. Read: FORM_VALIDATION_PATTERNS.md
2. Create: Yup schema
3. Choose: Formik or React Hook Form integration
4. Test: Form submission workflows

### "I'm getting an API error"
1. Check: Network tab (what response did you get?)
2. Read: ERROR_SCENARIOS.md (search error message)
3. Debug: DEBUGGING_GUIDE.md (section: Common Console Errors)
4. Fix: API_RESPONSE_PATTERNS.md (validation section)

### "My component render is broken"
1. Check: Browser console (any TypeScript/React errors?)
2. Search: ERROR_SCENARIOS.md for error message
3. Debug: DEBUGGING_GUIDE.md (Redux DevTools / Memory)
4. Review: IMPLEMENTATION_GUIDE.md Mistakes 1-23 (any patterns violated?)

### "I'm doing code review"
1. Use: CODE_REVIEW_CHECKLIST.md (comprehensive checklist)
2. Reference: COMPONENT_AUDIT_CHECKLIST.md (author checklist)
3. Link: Specific IMPLEMENTATION_GUIDE.md mistakes if violations found

### "My tests are failing"
1. Check: Test output (what assertion failed?)
2. Read: TESTING_PATTERNS.md (matching test type)
3. Verify: Mock data and assertions are correct
4. Debug: DEBUGGING_GUIDE.md (Memory leaks, async issues)

---

## 📖 Complete Guide List

### Core Migration Guides (Required Reading)
- **IMPLEMENTATION_GUIDE.md** - Core migration skill with Mistakes 1-23
- **PRE_MIGRATION_CHECKLIST.md** - Team preparation before migration starts
- **MIGRATION_RUNBOOK.md** - Phase-by-phase execution guide

### Development Pattern Guides (During Implementation)
- **MCA2_PAGE_LAYOUT_PATTERNS.md** - Page composition, spacing, layout, component hierarchy (from production MCA2 app)
- **COMPONENT_AUDIT_CHECKLIST.md** - Self-check before submitting PR
- **BLUEPRINT_REACT_CORRECT_PATTERNS.md** - Component usage patterns
- **BLUEPRINT_REACT_REFERENCE.md** - All Blueprint components & props
- **BDL_TO_BLUEPRINT_REACT.md** - Component mapping table (includes icon mapping in Section 8)
- **COMPONENT_DECOMPOSITION_PATTERNS.md** - Breaking monolithic components into sub-components
- **FOLDER_STRUCTURE.md** - Canonical MCA2 app directory layout and naming conventions
- **TYPESCRIPT_PATTERNS.md** - Type architecture, prop interfaces, Redux types, generics
- **NAVIGATION_PATTERNS.md** - MemoryRouter setup, route guards, navigation state, back button
- **CONDITIONAL_RENDERING_PATTERNS.md** - Show/hide fields, dynamic arrays, EJS migration patterns
- **STYLING_PATTERNS.md** - Blueprint styling, Grid layout, theming, responsive design
- **REDUX_PATTERNS.md** - Redux Toolkit patterns & best practices
- **FORM_VALIDATION_PATTERNS.md** - Yup, Formik, React Hook Form
- **API_RESPONSE_PATTERNS.md** - API integration & error handling

### Quality & Testing Guides
- **CODE_REVIEW_CHECKLIST.md** - Code review standards
- **COMPONENT_AUDIT_CHECKLIST.md** - Pre-PR component verification
- **TESTING_PATTERNS.md** - Unit, integration, E2E testing (Cypress & Playwright with MSW mocks)
- **ERROR_SCENARIOS.md** - 12 real scenarios with solutions

### Support & Troubleshooting
- **DEBUGGING_GUIDE.md** - DevTools and debugging techniques
- **ERROR_SCENARIOS.md** - Common errors and fixes

---

## 🔍 Search by Topic

### Architecture & Planning
- PRE_MIGRATION_CHECKLIST.md
- MIGRATION_RUNBOOK.md
- FOLDER_STRUCTURE.md (directory layout, naming conventions)
- REDUX_PATTERNS.md (Normalized State Design)

### React Components & UI
- BLUEPRINT_REACT_CORRECT_PATTERNS.md
- BLUEPRINT_REACT_REFERENCE.md
- BDL_TO_BLUEPRINT_REACT.md
- CONDITIONAL_RENDERING_PATTERNS.md (show/hide, dynamic fields)
- COMPONENT_DECOMPOSITION_PATTERNS.md

### TypeScript & Type Safety
- TYPESCRIPT_PATTERNS.md (entire document)
- IMPLEMENTATION_GUIDE.md (Key Considerations section)

### Navigation & Routing
- NAVIGATION_PATTERNS.md (entire document)
- IMPLEMENTATION_GUIDE.md (MemoryRouter setup in Step 5)

### State Management
- REDUX_PATTERNS.md (entire document)
- IMPLEMENTATION_GUIDE.md (Key Considerations section 6)

### Forms & Validation
- FORM_VALIDATION_PATTERNS.md (entire document)
- CONDITIONAL_RENDERING_PATTERNS.md (field visibility patterns)

### Styling & Layout
- MCA2_PAGE_LAYOUT_PATTERNS.md (page composition, Section/SectionItem spacing, Grid, button placement)
- STYLING_PATTERNS.md (entire document)
- BLUEPRINT_REACT_CORRECT_PATTERNS.md (Section/SectionItem usage)

### API Integration
- API_RESPONSE_PATTERNS.md (entire document)
- IMPLEMENTATION_GUIDE.md Mistake 23

### Testing & Quality
- TESTING_PATTERNS.md (reference only — tests not generated during migration)
- CODE_REVIEW_CHECKLIST.md
- COMPONENT_AUDIT_CHECKLIST.md

### Debugging & Troubleshooting
- DEBUGGING_GUIDE.md (entire document)
- ERROR_SCENARIOS.md (entire document)
- IMPLEMENTATION_GUIDE.md Mistakes 1-23

---

## ⚡ Common Quick Links

### I'm a developer - where do I start?
→ [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) then [BLUEPRINT_REACT_CORRECT_PATTERNS.md](BLUEPRINT_REACT_CORRECT_PATTERNS.md)

### I'm a team lead - how do I execute migration?
→ [PRE_MIGRATION_CHECKLIST.md](PRE_MIGRATION_CHECKLIST.md) then [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md)

### I'm a code reviewer - what should I check?
→ [CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md)

### I'm debugging an error - where do I look?
→ [ERROR_SCENARIOS.md](ERROR_SCENARIOS.md) or [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)

### I need to implement a feature - what pattern?
→ [BLUEPRINT_REACT_CORRECT_PATTERNS.md](BLUEPRINT_REACT_CORRECT_PATTERNS.md) or [REDUX_PATTERNS.md](REDUX_PATTERNS.md) or [FORM_VALIDATION_PATTERNS.md](FORM_VALIDATION_PATTERNS.md)

---

## 📋 Migration Phase Guide

### Phase 1: Pre-Migration (1-2 weeks)
- [ ] [PRE_MIGRATION_CHECKLIST.md](PRE_MIGRATION_CHECKLIST.md) - Complete team prep
- [ ] Read [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) Mistakes 1-23
- [ ] Read [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) Overview

### Phase 2: Setup (3-5 days)
- [ ] [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) - Steps 4-7
- [ ] Setup Redux store using [REDUX_PATTERNS.md](REDUX_PATTERNS.md)
- [ ] Create base components using [BLUEPRINT_REACT_CORRECT_PATTERNS.md](BLUEPRINT_REACT_CORRECT_PATTERNS.md)
- [ ] Setup API layer using [API_RESPONSE_PATTERNS.md](API_RESPONSE_PATTERNS.md)

### Phase 3: Development (2-3 weeks)
- [ ] [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) - Step 8
- [ ] Use [BLUEPRINT_REACT_CORRECT_PATTERNS.md](BLUEPRINT_REACT_CORRECT_PATTERNS.md) for UI
- [ ] Use [FORM_VALIDATION_PATTERNS.md](FORM_VALIDATION_PATTERNS.md) for forms
- [ ] Use [TESTING_PATTERNS.md](TESTING_PATTERNS.md) for tests
- [ ] Check [COMPONENT_AUDIT_CHECKLIST.md](COMPONENT_AUDIT_CHECKLIST.md) before PR

### Phase 4: Testing (3-5 days)
- [ ] [TESTING_PATTERNS.md](TESTING_PATTERNS.md) - Implement all test types
- [ ] [CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md) - Review all code
- [ ] [ERROR_SCENARIOS.md](ERROR_SCENARIOS.md) - Test error cases

### Phase 5: Deployment (1-2 days)
- [ ] [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) - Steps 16-19
- [ ] Final build verification
- [ ] Production deployment

---

## 📚 Reference Files (Created During Setup)

These files are created during initial skill setup:

- **BLUEPRINT_REACT_REFERENCE.md** - All Blueprint components & versions
- **EAGLE_FRAMEWORK_REFERENCE.md** - MCA2 framework details
- **LIBS_FOUNDATION_REFERENCE.md** - Foundation library details
- **MCA2_UI_LAUNCHER_REFERENCE.md** - UI launcher integration
- **BDL_TO_BLUEPRINT_REACT.md** - Component mapping table

---

## ✅ Success Checklist

Before considering migration complete:

**Technical**
- [ ] Build succeeds with 0 errors
- [ ] All TypeScript errors resolved
- [ ] 80%+ test coverage achieved
- [ ] All E2E tests passing
- [ ] Code review passed
- [ ] No IMPLEMENTATION_GUIDE.md Mistakes 1-23 violations

**Functional**
- [ ] Feature parity with MCA1 achieved
- [ ] All workflows tested
- [ ] All error scenarios handled
- [ ] User acceptance testing passed
- [ ] Stakeholder sign-off obtained

**Operational**
- [ ] Deployed to production
- [ ] Monitoring in place
- [ ] Team trained
- [ ] Documentation complete
- [ ] No critical issues in first week
- [ ] MCA1 decommissioned

---

## 🆘 Support & Questions

**Got a question?**
1. Search this index
2. Check relevant guide sections
3. Search [ERROR_SCENARIOS.md](ERROR_SCENARIOS.md)
4. Check [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) Mistakes 1-23

**Found a bug?**
1. Reproduce issue
2. Check [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)
3. Check [ERROR_SCENARIOS.md](ERROR_SCENARIOS.md)
4. Document and escalate

---

## 📝 Document Versions

| Document | Version | Last Updated |
|----------|---------|--------------|
| IMPLEMENTATION_GUIDE.md | 3.1 | April 16, 2026 |
| COMPONENT_AUDIT_CHECKLIST.md | 1.0 | March 25, 2026 |
| REDUX_PATTERNS.md | 1.0 | March 25, 2026 |
| FORM_VALIDATION_PATTERNS.md | 1.0 | March 25, 2026 |
| API_RESPONSE_PATTERNS.md | 1.0 | March 25, 2026 |
| TESTING_PATTERNS.md | 1.0 | March 25, 2026 |
| DEBUGGING_GUIDE.md | 1.0 | March 25, 2026 |
| ERROR_SCENARIOS.md | 1.0 | March 25, 2026 |
| MIGRATION_RUNBOOK.md | 1.0 | March 25, 2026 |
| CODE_REVIEW_CHECKLIST.md | 1.0 | March 25, 2026 |
| PRE_MIGRATION_CHECKLIST.md | 1.0 | March 25, 2026 |

---

## 🎓 Learning Path

**For developers new to MCA2:**

**Week 1:**
- Monday: Read IMPLEMENTATION_GUIDE.md (Mistakes 1-23)
- Tuesday: Review BLUEPRINT_REACT_CORRECT_PATTERNS.md
- Wednesday: Study REDUX_PATTERNS.md
- Thursday: Review FORM_VALIDATION_PATTERNS.md
- Friday: Study TESTING_PATTERNS.md

**Week 2:**
- Start implementing: Use BLUEPRINT_REACT_CORRECT_PATTERNS.md
- Review COMPONENT_AUDIT_CHECKLIST.md before PR
- Reference CODE_REVIEW_CHECKLIST.md during reviews
- Use DEBUGGING_GUIDE.md when issues arise

---

## 🔗 External Resources

- **React**: https://react.dev/learn
- **Redux Toolkit**: https://redux-toolkit.js.org
- **TypeScript**: https://www.typescriptlang.org/docs/
- **Jest**: https://jestjs.io/docs/getting-started
- **Cypress**: https://docs.cypress.io
- **Yup**: https://github.com/jquense/yup
- **Formik**: https://formik.org
- **React Hook Form**: https://react-hook-form.com

---

## 📞 Escalation Path

**Issue Type** → **First Check** → **Next Step** → **Escalate To**

- Build error → ERROR_SCENARIOS.md → DEBUGGING_GUIDE.md → Team Lead
- Component issue → BLUEPRINT_REACT_CORRECT_PATTERNS.md → IMPLEMENTATION_GUIDE.md → Reviewer
- Redux issue → REDUX_PATTERNS.md → DEBUGGING_GUIDE.md → Tech Lead
- API issue → API_RESPONSE_PATTERNS.md → ERROR_SCENARIOS.md → Backend Team
- Test failure → TESTING_PATTERNS.md → DEBUGGING_GUIDE.md → QA Lead

---

## 🎯 Key Takeaways

✅ **Always check these first:**
1. IMPLEMENTATION_GUIDE.md Mistakes 1-23
2. COMPONENT_AUDIT_CHECKLIST.md (before PR)
3. ERROR_SCENARIOS.md (when debugging)

✅ **Use these during development:**
1. BLUEPRINT_REACT_CORRECT_PATTERNS.md
2. REDUX_PATTERNS.md
3. API_RESPONSE_PATTERNS.md
4. FORM_VALIDATION_PATTERNS.md

✅ **Remember these principles:**
1. Array.isArray() checks (Mistake 23)
2. Initialize API in Entry.tsx (Mistake 22)
3. FormItem render function pattern (Mistake 3)
4. No custom CSS for Blueprint (Mistake 1)
5. Use MemoryRouter, not BrowserRouter (Mistake 22)

---

Good luck with your migration! 🚀
