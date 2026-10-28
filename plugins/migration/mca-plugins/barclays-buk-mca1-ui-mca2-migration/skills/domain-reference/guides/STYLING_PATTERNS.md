# Styling Patterns for MCA2

CSS, layout, theming, and responsive design patterns for migrated MCA2 Blueprint-React applications.

Last Updated: 2026-05-19 | Version: 1.0.0

---

## Table of Contents

1. [Core Principle: Blueprint Handles Styling](#core-principle-blueprint-handles-styling)
2. [Layout with Grid](#layout-with-grid)
3. [Spacing with Section and SectionItem](#spacing-with-section-and-sectionitem)
4. [Typography](#typography)
5. [When Custom CSS IS Needed](#when-custom-css-is-needed)
6. [Responsive Design](#responsive-design)
7. [Theming and Micro-Themes](#theming-and-micro-themes)
8. [Animation Patterns](#animation-patterns)
9. [Anti-Patterns](#anti-patterns)

---

## Core Principle: Blueprint Handles Styling

Blueprint-React components come pre-styled. They include their own CSS, spacing, colors, typography, and responsive behavior. Do NOT override with custom CSS modules.

**Rule:** If you're reaching for a `.module.css` file to style a Blueprint component, you're doing it wrong. Use Blueprint's built-in props instead.

```typescript
// ❌ WRONG — custom CSS module to style a Button
import styles from './Button.module.css';
<Button className={styles.dangerButton}>Delete</Button>

// ✓ CORRECT — Blueprint's built-in status prop
<Button status="danger">Delete</Button>
```

```typescript
// ❌ WRONG — custom spacing with CSS
import styles from './Form.module.css';
<div className={styles.formSection}>...</div>

// ✓ CORRECT — Blueprint's spacing components
<Section>
  <SectionItem spacing="md">...</SectionItem>
</Section>
```

---

## Layout with Grid

Use Blueprint's `Grid` and `Grid.Col` for column layouts.

### Basic Two-Column Layout

```typescript
import { Grid } from '@barclays/blueprint-react';

const DashboardPage: React.FC = () => (
  <Grid>
    <Grid.Col sm={12} md={6}>
      <RoleSummaryCard />
    </Grid.Col>
    <Grid.Col sm={12} md={6}>
      <ServiceStatusCard />
    </Grid.Col>
  </Grid>
);
```

### Form Layout (Label Left, Input Right)

```typescript
<Grid>
  <Grid.Col sm={12} md={4}>
    <Type>Account Name</Type>
  </Grid.Col>
  <Grid.Col sm={12} md={8}>
    <FormItem
      render={(props) => <FormInput {...props} id="accountName" value={name} onChange={...} />}
    />
  </Grid.Col>
</Grid>
```

### Grid Breakpoint Props

| Prop | Breakpoint | Typical Use |
|------|-----------|-------------|
| `xs` | <576px | Mobile |
| `sm` | >=576px | Small tablet |
| `md` | >=768px | Tablet/small desktop |
| `lg` | >=992px | Desktop |
| `xl` | >=1200px | Large desktop |

Values are column spans out of 12: `sm={6}` = half width on small screens.

---

## Spacing with Section and SectionItem

`Section` and `SectionItem` manage vertical spacing between content blocks.

### Correct Usage

```typescript
import { Section, SectionItem } from '@barclays/blueprint-react';

const RoleForm: React.FC = () => (
  <Section>
    <SectionItem>
      <Type variant="heading">Create Role</Type>
    </SectionItem>
    <SectionItem>
      <FormItem label={<Type>Role Name</Type>} render={(props) => (
        <FormInput {...props} id="roleName" value={name} onChange={...} />
      )} />
    </SectionItem>
    <SectionItem>
      <FormItem label={<Type>Description</Type>} render={(props) => (
        <FormTextarea {...props} id="roleDesc" value={desc} onChange={...} />
      )} />
    </SectionItem>
    <SectionItem>
      <Button type="submit">Create</Button>
    </SectionItem>
  </Section>
);
```

### Spacing Rules

- Group related content in ONE `SectionItem` (title + subtitle together, not separate)
- Maximum 2-3 `SectionItem`s per `Section` to avoid excessive whitespace
- Do NOT wrap every single element in its own `SectionItem`
- Use `Section` as the top-level page container

```typescript
// ❌ WRONG — excessive nesting creates whitespace bloat
<Section>
  <SectionItem><Type variant="heading">Title</Type></SectionItem>
  <SectionItem><Type>Subtitle</Type></SectionItem>
  <SectionItem><FormItem ... /></SectionItem>
  <SectionItem><FormItem ... /></SectionItem>
  <SectionItem><FormItem ... /></SectionItem>
  <SectionItem><Button>Submit</Button></SectionItem>
</Section>

// ✓ CORRECT — grouped logically
<Section>
  <SectionItem>
    <Type variant="heading">Title</Type>
    <Type>Subtitle</Type>
  </SectionItem>
  <SectionItem>
    <FormItem ... />
    <FormItem ... />
    <FormItem ... />
  </SectionItem>
  <SectionItem>
    <Button>Submit</Button>
  </SectionItem>
</Section>
```

---

## Typography

All visible text must be wrapped in Blueprint's `<Type>` component.

```typescript
import { Type } from '@barclays/blueprint-react';

// Heading
<Type variant="heading" size="lg">Page Title</Type>

// Subheading
<Type variant="heading" size="md">Section Title</Type>

// Body text
<Type>This is body text.</Type>

// Small/secondary text
<Type size="sm" color="secondary">Last updated: 2026-05-19</Type>

// Error text
<Type color="error">This field is required</Type>

// Bold
<Type weight="bold">Important</Type>
```

**Rules:**
- Never use bare text outside `<Type>` — it won't inherit Blueprint typography
- Never use HTML heading tags (`<h1>`, `<h2>`) — use `<Type variant="heading" size="...">`
- Error messages always use `<Type color="error">`

---

## When Custom CSS IS Needed

Custom CSS is acceptable for:

1. **Page-level layout** — positioning sections that Blueprint components don't handle
2. **Animations/transitions** — show/hide transitions, loading pulses
3. **Third-party component wrappers** — styling non-Blueprint elements
4. **Print styles** — `@media print` rules

### How to Add Custom CSS

Use CSS Modules (`.module.css`) ONLY for the cases above — never for Blueprint components.

```typescript
// src/pages/Dashboard/Dashboard.module.css
.dashboardGrid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
  padding: 16px;
}

.fadeIn {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

```typescript
// src/pages/Dashboard/Dashboard.tsx
import styles from './Dashboard.module.css';

const Dashboard: React.FC = () => (
  <div className={styles.dashboardGrid}>
    <aside>...</aside>
    <main>...</main>
  </div>
);
```

---

## Responsive Design

### Blueprint Grid Handles Most Cases

```typescript
<Grid>
  {/* Full width on mobile, half on tablet, third on desktop */}
  <Grid.Col xs={12} sm={6} lg={4}>
    <Card />
  </Grid.Col>
</Grid>
```

### Hiding Elements by Breakpoint

When an element should only show on certain screen sizes:

```typescript
// Use CSS module for responsive visibility (Blueprint doesn't have a show/hide utility)
// src/components/common/responsive.module.css
.mobileOnly {
  display: block;
}
@media (min-width: 768px) {
  .mobileOnly { display: none; }
}

.desktopOnly {
  display: none;
}
@media (min-width: 768px) {
  .desktopOnly { display: block; }
}
```

---

## Theming and Micro-Themes

Blueprint components inherit their theme from the provider. Do NOT hardcode colors.

```typescript
// ❌ WRONG — hardcoded color
<div style={{ backgroundColor: '#003B6F' }}>...</div>

// ✓ CORRECT — use Blueprint components which inherit theme
<Section>
  <SectionItem>...</SectionItem>
</Section>
```

### Micro-Theme Variants

For sections that need a different visual treatment (e.g., highlighted card):

```typescript
import { BarclaysMicroTheme } from '@barclays/blueprint-react';

<BarclaysMicroTheme variant="highlight">
  <Section>
    <SectionItem>
      <Type>This section has a highlighted theme variant</Type>
    </SectionItem>
  </Section>
</BarclaysMicroTheme>
```

---

## Animation Patterns

Use CSS transitions for show/hide. No JavaScript animation libraries needed.

### Fade In/Out

```css
/* src/components/common/animations.module.css */
.fadeEnter {
  opacity: 0;
  transition: opacity 0.2s ease-in;
}

.fadeEnterActive {
  opacity: 1;
}

.fadeExit {
  opacity: 1;
  transition: opacity 0.2s ease-out;
}

.fadeExitActive {
  opacity: 0;
}
```

### Collapse/Expand

```css
.collapse {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease-out;
}

.collapseOpen {
  max-height: 500px;
}
```

```typescript
import styles from './animations.module.css';

const CollapsibleSection: React.FC<{ isOpen: boolean; children: React.ReactNode }> = ({
  isOpen,
  children,
}) => (
  <div className={`${styles.collapse} ${isOpen ? styles.collapseOpen : ''}`}>
    {children}
  </div>
);
```

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| `.module.css` for Blueprint components | Fights Blueprint's built-in styling | Use component props |
| Inline `style={{}}` for theming | Doesn't respond to theme changes | Use `<Type>`, `<Section>`, Blueprint props |
| `!important` in CSS | Fragile, unmaintainable | Remove; use correct component props |
| Hardcoded color values | Won't adapt to theme/dark mode | Use Blueprint theme system |
| Custom font-size/font-family | Breaks typography consistency | Use `<Type>` with size prop |
| `<div>` for layout spacing | Inconsistent gaps, no responsiveness | Use `<Section>`, `<SectionItem>`, `<Grid>` |
| Overriding Blueprint class names | Breaks on version updates | Use exposed props or wrap in your own component |
| CSS-in-JS libraries (styled-components) | Unnecessary complexity, bundle size | Use Blueprint + CSS Modules for edge cases |
