# Blueprint React Component Library Reference

## Overview
**Version**: 0.0.0
**Repository**: @barclays/blueprint-react
**Type**: React component library
**Build System**: Rollup (lib), Vite (app/storybook)
**Testing**: Jest with React Testing Library
**Storybook**: 8.6.3

## Key Technologies
- React: v17 || v18 || v19
- TypeScript: 5.5.3
- Styled Components: 6.1.12
- CSS Modules with Blueprint CSS
- React Hook Form: 7.62.0
- Formik: 2.4.6
- Focus Trap React: 11.0.4

## Component Library Structure

### Total Components: 82 (exported from lib/index.ts)

#### Core UI Components (lib/src/)
- **Account** (account)
- **Account Card** (account-card)
- **Accordion** (accordion, accordion-item)
- **Alert** (alert)
- **Arrange** (arrange)
- **AutoComplete** (autocomplete)
- **Badge** (badge)
- **Banner** (banner, slim-banner, mini-banner)
- **Box** (box)
- **Brand Logo** (brand-logo)
- **Breadcrumbs** (breadcrumbs)
- **Brick** (brick)
- **Button** (button, button-link, button-label, button-group)
- **Carousel** (carousel)
- **Chip** (chip, chip-group)
- **Complex Dropdown** (complex-dropdown)
- **Content** (content)
- **Control Pane** (control-pane)
- **Control Panel** (control-panel)
- **Currency** (currency)
- **Description List** (description-list)
- **Dialog** (dialog)
- **Drag & Drop** (drag-drop)
- **Drawer Sheet** (drawer-sheet)
- **Footer** (footer)
- **Form Components**:
  - form
  - form-button
  - form-checkbox
  - form-input
  - form-input-with-range
  - form-item
  - form-multi-item
  - form-radio
  - form-select
  - form-textarea
- **Ghost** (ghost)
- **Grid** (grid)
- **Hero** (hero, hero-alert)
- **Icon** (icon)
- **Indicator** (indicator)
- **Insight Card** (insight-card)
- **Link** (link)
- **List** (list)
- **Loading** (loading)
- **Media Section** (media-section)
- **Menu Icon** (menu-icon)
- **Micro Theme** (micro-theme)
- **Modal** (modal)
- **Multimedia** (multimedia)
- **Nav** (nav)
- **Navbar** (navbar)
- **Notification** (notification)
- **Number Stepper** (number-stepper)
- **Overlay** (overlay)
- **Page** (page)
- **Pagination** (pagination, pagination-simple)
- **Panel** (panel)
- **Pips** (pips)
- **Popup Nav** (popup-nav)
- **Progress** (progress, progress-bar, progress-circular, progress-vertical)
- **Quicklink** (quicklink)
- **Screen Reader** (screen-reader)
- **Search Dropdown** (search-dropdown)
- **Section** (section)
- **Segmented Buttons** (segmented-buttons)
- **Segmented Navigation** (segmented-navigation)
- **Separator** (separator)
- **Tab Link** (tab-link)
- **Table** (table)
- **Tabs** (tabs)
- **Theme Provider** (theme-provider)
- **Tile** (tile)
- **Toast** (toast)
- **Typography** (typography)

### Patterns (lib/patterns/)
- **Global Navigation** (global-navigation)
- **Responsive Table** (responsive-table)
- **Search Field** (search-field)

## Component Architecture

### TypeScript-First Approach
Each component follows this pattern:

1. **Component Interface** (e.g., `button.interface.ts`)
   - Defines `CommonButtonProps` with variant, status, size, media, etc.

2. **Custom Hooks** (e.g., `button-classes.hook.ts`)
   - Use `useMemo` for performance optimization
   - Build CSS class names using classnames utility
   - Import styles from Blueprint CSS modules

3. **Component Implementation** (e.g., `button.component.tsx`)
   ```typescript
   export const Button = forwardRef<HTMLButtonElement, ButtonComponentProps>(
     ({ variant, status, size, ... }, ref) => {
       const cssClass = useButtonClasses(...);
       return (
         <button className={cssClass} ref={ref} {...rest}>
           {/* content */}
         </button>
       );
     }
   );
   ```

4. **Index Export** (e.g., `index.ts`)
   - Re-exports all component parts

### CSS Styling Strategy
- **CSS Modules** from @barclays/blueprint-css
- Module imports: `import styles from "@barclays/blueprint-css/components/button/dist/index.module.css"`
- Class composition with classnames utility
- No CSS-in-JS generation, only CSS Module usage

### Build Configuration

**Library Build** (lib/rollup.config.js):
- TypeScript compilation
- Rollup bundling
- CSS Module support
- External peer dependencies (react, react-dom)

**App/Storybook Build** (app/vite.config.build.ts):
- Vite configuration
- Component showcase application

## Dependencies

### Production Dependencies
- @barclays/blueprint-css: ^1.2.0
- @barclays/blueprint-icons: ^1.2.0
- @react-aria/live-announcer: ^3.4.4
- aria-hidden: ^1.2.6
- classnames: ^2.5.1
- focus-trap-react: ^11.0.4
- react-dropzone: ^14.3.5
- react-transition-group: ^4.4.5
- react-use: ^17.5.0

### Development Dependencies
- Storybook: 8.6.3
- Jest: 29.7.0
- React Testing Library: 16.3.0
- TypeScript: 5.5.3
- Rollup: 4.18.0
- Vite: 5.4.0

## NPM Scripts
- `npm start` - Storybook dev server (port 6007)
- `npm run build` - Build library and app
- `npm run test` - Run Jest tests
- `npm run lint` - ESLint and Prettier
- `npm run fix` - Auto-fix linting issues
- `npm run mutation` - Stryker mutation testing

## Key Files
- `lib/index.ts` - Main export file (82 exports)
- `lib/src/*/index.ts` - Component exports
- `lib/patterns/` - Reusable patterns
- `.storybook/preview.tsx` - Storybook configuration
- `jest.config.ts` - Jest configuration
