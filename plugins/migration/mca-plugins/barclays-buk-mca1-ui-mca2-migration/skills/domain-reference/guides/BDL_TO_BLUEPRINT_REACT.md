# BDL to Blueprint-React Component Mapping

**Last Updated**: April 24, 2026
**Version**: 4.0
**Status**: Split into per-component mapping files in `mappings/` directory

## Overview

This document maps MCA1 BDL (Barclays Design Language) web components to Blueprint-React equivalents. MCA1 BDL components use the `<mca-*>` naming convention in EJS templates. All Blueprint-React form components **must** use the `FormItem` + render function pattern.

Each component has its own detailed mapping file in the `mappings/` directory with before/after examples and complete attribute mapping tables.

---

## Component Mapping Files

### Form Controls

**Critical Pattern**: All form fields in Blueprint-React must be wrapped in `<FormItem>` with a `render` function. Do NOT use children wrapping.

| MCA1 Component | Blueprint-React | Mapping File |
|---|---|---|
| `<mca-input>` | `<FormItem>` + `<FormInput>` | [BDL_INPUT_MAPPING.md](../mappings/BDL_INPUT_MAPPING.md) |
| `<mca-radios>` / `<mca-radio>` | `<FormMultiItem>` + `<FormRadio>` | [BDL_RADIO_MAPPING.md](../mappings/BDL_RADIO_MAPPING.md) |
| `<mca-checkboxes>` / `<mca-checkbox>` | `<FormMultiItem>` + `<FormCheckbox>` | [BDL_CHECKBOX_MAPPING.md](../mappings/BDL_CHECKBOX_MAPPING.md) |
| `<mca-combobox>` | `<FormItem>` + `<FormSelect>` / `<AutoComplete>` | [BDL_COMBOBOX_MAPPING.md](../mappings/BDL_COMBOBOX_MAPPING.md) |
| `<mca-textarea>` | `<FormItem>` + `<FormTextarea>` | [BDL_TEXTAREA_MAPPING.md](../mappings/BDL_TEXTAREA_MAPPING.md) |
| `<mca-sortaccount>` | `<FormMultiItem>` + `<FormItem hiddenLabel>` + `<FormInput>` | [BDL_SORTACCOUNT_MAPPING.md](../mappings/BDL_SORTACCOUNT_MAPPING.md) |
| `<mca-date>`, `<mca-cardnumber>`, `<mca-form>`, etc. | Various `<FormItem>` patterns | [BDL_FORM_CONTROLS_MAPPING.md](../mappings/BDL_FORM_CONTROLS_MAPPING.md) |
| `<mca-stepper>` | `<NumberStepper>` | [BDL_STEPPER_MAPPING.md](../mappings/BDL_STEPPER_MAPPING.md) |

### UI Components

| MCA1 Component | Blueprint-React | Mapping File |
|---|---|---|
| `<mca-button>` / `<mca-button-groups>` | `<Button>`, `<ButtonLink>`, `<FormMultiItem>` + `<FormRadio>` | [BDL_BUTTON_MAPPING.md](../mappings/BDL_BUTTON_MAPPING.md) |
| `<mca-link>` | `<Link>` | [BDL_LINK_MAPPING.md](../mappings/BDL_LINK_MAPPING.md) |
| `<mca-fluidview>`, `<mca-cell>`, `<mca-header>`, `<mca-footer>` | `<Grid>`, `<Page>`, `<Navbar>` | [BDL_LAYOUT_MAPPING.md](../mappings/BDL_LAYOUT_MAPPING.md) |
| `<mca-modal>` | `<Dialog>` or `<Modal>` (ref-based) | [BDL_DIALOG_MAPPING.md](../mappings/BDL_DIALOG_MAPPING.md) |
| `<mca-heading>` / `<mca-text>` | `<Type>` | [BDL_TYPOGRAPHY_MAPPING.md](../mappings/BDL_TYPOGRAPHY_MAPPING.md) |
| `<mca-notify>` | `<Alert>` | [BDL_NOTIFY_MAPPING.md](../mappings/BDL_NOTIFY_MAPPING.md) |
| `<mca-table>`, `<mca-table-row>`, `<mca-table-cell>` | `<Table>` + standard HTML `<tr>/<td>/<th>` | [BDL_TABLE_MAPPING.md](../mappings/BDL_TABLE_MAPPING.md) |
| `<mca-account-table>` | `PaginatedTable` from `@barclays/mca-ui-common-utils-paginated-table` | [BDL_TABLE_MAPPING.md](../mappings/BDL_TABLE_MAPPING.md) |
| `<mca-infopair>`, `<mca-list>`, `<mca-progressbar>` | `<DescriptionList>`, `<List>`, `<Progress>` | [BDL_DATA_DISPLAY_MAPPING.md](../mappings/BDL_DATA_DISPLAY_MAPPING.md) |
| `<mca-icon>` | `<Icon>` | [BDL_ICON_MAPPING.md](../mappings/BDL_ICON_MAPPING.md) |
| `<mca-image>` | `<Multimedia>` | [BDL_IMAGE_MAPPING.md](../mappings/BDL_IMAGE_MAPPING.md) |
| `<mca-accordion>` / `<mca-separator>` | `<Accordion>` / `<Separator>` | [BDL_ACCORDION_MAPPING.md](../mappings/BDL_ACCORDION_MAPPING.md) |
| `<mca-tabs>` / `<mca-tab>` | `<Tabs>` + `<Tab>` | [BDL_TABS_MAPPING.md](../mappings/BDL_TABS_MAPPING.md) |
| `<mca-statusbar>` | `<SlimBanner>` + MicroTheme | [BDL_STATUSBAR_MAPPING.md](../mappings/BDL_STATUSBAR_MAPPING.md) |
| `<mca-spinner>` | `<Loading>` | [BDL_SPINNER_MAPPING.md](../mappings/BDL_SPINNER_MAPPING.md) |
| `<mca-popover>` | `<PopupNav>` | [BDL_POPOVER_MAPPING.md](../mappings/BDL_POPOVER_MAPPING.md) |

---

## Complete Component Inventory

All 48 MCA1 BDL components:

| # | MCA1 Component | Blueprint-React Equivalent | Pattern | Mapping File |
|---|---|---|---|---|
| 1 | `<mca-accordion>` | `<Accordion>` | Direct | [Accordion](../mappings/BDL_ACCORDION_MAPPING.md) |
| 2 | `<mca-accordionitem>` | Accordion children | Direct | [Accordion](../mappings/BDL_ACCORDION_MAPPING.md) |
| 3 | `<mca-button>` | `<Button>` | Attribute remapping | [Button](../mappings/BDL_BUTTON_MAPPING.md) |
| 3b | `<mca-button-groups>` | `<FormMultiItem>` + `<FormRadio>` or `<Arrange>` + `<Button>` | Data-driven | [Button](../mappings/BDL_BUTTON_MAPPING.md) |
| 4 | `<mca-cardnumber>` | `<FormItem>` + `<FormInput>` | Render function | [Form Controls](../mappings/BDL_FORM_CONTROLS_MAPPING.md) |
| 5 | `<mca-cell>` | `<Grid.Col>` | Size mapping | [Layout](../mappings/BDL_LAYOUT_MAPPING.md) |
| 6 | `<mca-checkbox>` | `<FormCheckbox>` | Render function | [Checkbox](../mappings/BDL_CHECKBOX_MAPPING.md) |
| 7 | `<mca-checkboxes>` | `<FormMultiItem>` wrapping `<FormCheckbox>` | Children pattern | [Checkbox](../mappings/BDL_CHECKBOX_MAPPING.md) |
| 8 | `<mca-combobox template="dropdown">` | `<FormItem>` + `<FormSelect>` | Render function | [Combobox](../mappings/BDL_COMBOBOX_MAPPING.md) |
| 9 | `<mca-combobox template="autocomplete">` | `<FormItem>` + `<AutoComplete>` | Render function | [Combobox](../mappings/BDL_COMBOBOX_MAPPING.md) |
| 10 | `<mca-combobox-option>` | `<option>` (standard HTML) | Direct | [Combobox](../mappings/BDL_COMBOBOX_MAPPING.md) |
| 11 | `<mca-date>` | `<FormItem>` + `<FormInput>` + validation | Render function | [Form Controls](../mappings/BDL_FORM_CONTROLS_MAPPING.md) |
| 12 | `<mca-dropdown-account>` | `<FormItem>` + `<FormSelect>` | Render function | [Form Controls](../mappings/BDL_FORM_CONTROLS_MAPPING.md) |
| 13 | `<mca-dropdown-expiry-date>` | Two `<FormItem>` + `<FormSelect>` | Render function | [Form Controls](../mappings/BDL_FORM_CONTROLS_MAPPING.md) |
| 14 | `<mca-fluidview>` | `<Grid>` | Direct | [Layout](../mappings/BDL_LAYOUT_MAPPING.md) |
| 15 | `<mca-footer>` | `<Page>` footer or `<Section>` | Layout restructure | [Layout](../mappings/BDL_LAYOUT_MAPPING.md) |
| 16 | `<mca-form>` | `<Form>` | Direct | [Form Controls](../mappings/BDL_FORM_CONTROLS_MAPPING.md) |
| 17 | `<mca-formview>` | `<Form>` or container | Direct | [Form Controls](../mappings/BDL_FORM_CONTROLS_MAPPING.md) |
| 18 | `<mca-header>` | `<Page head={<Navbar>}>` | Layout restructure | [Layout](../mappings/BDL_LAYOUT_MAPPING.md) |
| 19 | `<mca-heading>` | `<Type element="hN">` | Attribute remapping | [Typography](../mappings/BDL_TYPOGRAPHY_MAPPING.md) |
| 20 | `<mca-icon>` | `<Icon>` | Attribute remapping | [Icon](../mappings/BDL_ICON_MAPPING.md) |
| 21 | `<mca-image>` | `<Multimedia>` | Attribute remapping | [Image](../mappings/BDL_IMAGE_MAPPING.md) |
| 22 | `<mca-info-container>` | `<Section>` or `<DescriptionList>` | Layout restructure | [Data Display](../mappings/BDL_DATA_DISPLAY_MAPPING.md) |
| 23 | `<mca-infopair>` | `<DescriptionList>` dt/dd or `<Type>` pairs | Layout restructure | [Data Display](../mappings/BDL_DATA_DISPLAY_MAPPING.md) |
| 24 | `<mca-input>` | `<FormItem>` + `<FormInput>` | Render function | [Input](../mappings/BDL_INPUT_MAPPING.md) |
| 25 | `<mca-link>` | `<Link>` | Attribute remapping | [Link](../mappings/BDL_LINK_MAPPING.md) |
| 26 | `<mca-list>` | `<List>` or standard `<ul>`/`<ol>` | Direct | [Data Display](../mappings/BDL_DATA_DISPLAY_MAPPING.md) |
| 27 | `<mca-list-item>` | `<li>` | Direct | [Data Display](../mappings/BDL_DATA_DISPLAY_MAPPING.md) |
| 28 | `<mca-modal>` | `<Dialog>` or `<Modal>` | Slot properties / Ref-based | [Dialog](../mappings/BDL_DIALOG_MAPPING.md) |
| 29 | `<mca-modal-body>` | `children` of `<Dialog>` | Absorbed into Dialog | [Dialog](../mappings/BDL_DIALOG_MAPPING.md) |
| 30 | `<mca-modal-footer>` | `foot` prop of `<Dialog>` | Absorbed into Dialog | [Dialog](../mappings/BDL_DIALOG_MAPPING.md) |
| 31 | `<mca-notify>` | `<Alert>` | Attribute remapping | [Notify](../mappings/BDL_NOTIFY_MAPPING.md) |
| 32 | `<mca-progressbar>` | `<Progress>` | Attribute remapping | [Data Display](../mappings/BDL_DATA_DISPLAY_MAPPING.md) |
| 33 | `<mca-radio>` | `<FormRadio>` (inside `<FormItem>` render) | Render function | [Radio](../mappings/BDL_RADIO_MAPPING.md) |
| 34 | `<mca-radios>` | `<FormMultiItem>` wrapping `<FormRadio>` | Render function | [Radio](../mappings/BDL_RADIO_MAPPING.md) |
| 35 | `<mca-selection>` | `<FormItem>` + `<FormSelect>` or `<AutoComplete>` | Render function | [Form Controls](../mappings/BDL_FORM_CONTROLS_MAPPING.md) |
| 36 | `<mca-separator>` | `<Separator>` | Direct | [Accordion](../mappings/BDL_ACCORDION_MAPPING.md) |
| 37 | `<mca-sortaccount>` | `<FormMultiItem>` + nested `<FormItem hiddenLabel>` + `<FormInput>` | Render function | [Sort Code & Account](../mappings/BDL_SORTACCOUNT_MAPPING.md) |
| 38 | `<mca-table>` | `<Table>` + standard HTML | HTML elements | [Table](../mappings/BDL_TABLE_MAPPING.md) |
| 39 | `<mca-table-row>` | `<tr>` | Standard HTML | [Table](../mappings/BDL_TABLE_MAPPING.md) |
| 40 | `<mca-table-cell>` | `<td>` or `<th>` | Standard HTML | [Table](../mappings/BDL_TABLE_MAPPING.md) |
| 41 | `<mca-account-table>` | `PaginatedTable` from `@barclays/mca-ui-common-utils-paginated-table` | Package import | [Table](../mappings/BDL_TABLE_MAPPING.md) |
| 42 | `<mca-text>` | `<Type>` | Attribute remapping | [Typography](../mappings/BDL_TYPOGRAPHY_MAPPING.md) |
| 43 | `<mca-textarea>` | `<FormItem>` + `<FormTextarea>` | Render function | [Textarea](../mappings/BDL_TEXTAREA_MAPPING.md) |
| 44 | `<mca-tabs>` | `<Tabs>` | Direct | [Tabs](../mappings/BDL_TABS_MAPPING.md) |
| 45 | `<mca-tab>` | `<Tab>` | Direct | [Tabs](../mappings/BDL_TABS_MAPPING.md) |
| 46 | `<mca-statusbar>` | `<SlimBanner>` + MicroTheme | Attribute remapping | [StatusBar](../mappings/BDL_STATUSBAR_MAPPING.md) |
| 47 | `<mca-spinner>` | `<Loading>` | Attribute remapping | [Spinner](../mappings/BDL_SPINNER_MAPPING.md) |
| 48 | `<mca-popover>` | `<PopupNav>` | Hook-based | [Popover](../mappings/BDL_POPOVER_MAPPING.md) |
| 49 | `<mca-stepper>` | `<NumberStepper>` | Attribute remapping | [Stepper](../mappings/BDL_STEPPER_MAPPING.md) |

---

## Common Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Notes |
|---|---|---|
| `id` | `id` | Same |
| `name` | `name` | Same |
| `class` | `className` | React convention |
| `disabled="yes"` | `disabled` | Boolean in React |
| `required="yes"` | Validation via Yup | Not a direct prop on FormItem |
| `placeholder` | `placeholder` | Same |
| `value` | `value` | Controlled component |
| `checked="no"` | `checked={false}` | Boolean in React |
| Text content (label) | `label` prop on `FormItem` | Moved to FormItem |
| `aria-label` | `aria-label` | Same |
| `align` | Layout via `<Arrange>` or `<Grid>` | Not a direct prop |

---

## Additional Web Component Mapping Files

These cover BDL web components not in the original 48-component inventory:

| MCA1 Component | Blueprint-React | Mapping File |
|---|---|---|
| `<mca-file-upload>` | `DragDrop` + `SimpleFileUpload` | [BDL_FILE_UPLOAD_MAPPING.md](../mappings/BDL_FILE_UPLOAD_MAPPING.md) |
| `<mca-calendar>` | `@barclays/mca-react-calendar` (external) | [BDL_CALENDAR_MAPPING.md](../mappings/BDL_CALENDAR_MAPPING.md) |
| `<mca-progressive>` / `<mca-progressiveitem>` | `ProgressVertical` + `ProgressVerticalItem` | [BDL_PROGRESSIVE_MAPPING.md](../mappings/BDL_PROGRESSIVE_MAPPING.md) |
| `<mca-time>` (DEPRECATED) | `FormSelect` with time options | [BDL_TIME_MAPPING.md](../mappings/BDL_TIME_MAPPING.md) |
| Validation patterns | Yup + `FormItem` error + `Alert` | [BDL_VALIDATION_PATTERNS_MAPPING.md](../mappings/BDL_VALIDATION_PATTERNS_MAPPING.md) |

---

## Legacy Component Mapping Files

MCA1 applications may also contain **legacy jQuery-based components** that predate the `<mca-*>` web component layer. These use `steal()` module loading, jQuery plugins (`.chosen()`, `.scpTable()`, `.expandable()`), and `scp-` CSS classes. Each file below covers a category of related legacy patterns:

| Category | Legacy Components | Blueprint Target | Mapping File |
|----------|------------------|-----------------|--------------|
| Autocomplete | `.scpAutoComplete()`, custom item builder | `Autocomplete` | [LEGACY_AUTOCOMPLETE_MAPPING.md](../mappings/LEGACY_AUTOCOMPLETE_MAPPING.md) |
| Dialogs & Tooltips | `.dialog()`, popup, tooltip, inlineTooltip | `Dialog`, `Icon` + `title` attr | [LEGACY_DIALOG_TOOLTIP_MAPPING.md](../mappings/LEGACY_DIALOG_TOOLTIP_MAPPING.md) |
| Dropdowns | All 11 Chosen-based dropdown variants | `FormSelect`, `Autocomplete`, `Checkbox` group | [LEGACY_DROPDOWN_MAPPING.md](../mappings/LEGACY_DROPDOWN_MAPPING.md) |
| DataTables | `.scpTable()` — 6 jQuery DataTable variants | `Table` + `Pagination` + custom hooks | [LEGACY_DATATABLE_MAPPING.md](../mappings/LEGACY_DATATABLE_MAPPING.md) |
| Labels | label, labelIcon, labelReadOnly | `Type` + `Icon`, `FormItem` label prop | [LEGACY_LABELS_MAPPING.md](../mappings/LEGACY_LABELS_MAPPING.md) |
| Typography | content (font styles), legacyHeading | `Type` with `element`/`size`/`weight` | [LEGACY_TYPOGRAPHY_MAPPING.md](../mappings/LEGACY_TYPOGRAPHY_MAPPING.md) |
| Accordion & Tabs | legacyAccordion, legacyTab, tabNested | `Accordion` + `AccordionItem`, `Tabs` + `Tab` | [LEGACY_ACCORDION_TABS_MAPPING.md](../mappings/LEGACY_ACCORDION_TABS_MAPPING.md) |
| Layout | grid, separator, header, footer | `Grid` + `Grid.Col`, `Separator`, `Arrange` | [LEGACY_LAYOUT_MAPPING.md](../mappings/LEGACY_LAYOUT_MAPPING.md) |
| Miscellaneous | message, spinner, progressBar, progressiveDisclosure, buttonWithIcon | `Alert`, `Loading`, `ProgressVertical`, `Button` + `media` | [LEGACY_MISC_MAPPING.md](../mappings/LEGACY_MISC_MAPPING.md) |
| Calendar & Custom | eventCalendar, selectToRadio, validation framework | `@barclays/mca-react-calendar`, `FormRadio`, Yup | [LEGACY_CALENDAR_CUSTOM_MAPPING.md](../mappings/LEGACY_CALENDAR_CUSTOM_MAPPING.md) |

---

## Version History

### v5.0 (July 7, 2026) - LEGACY COMPONENT COVERAGE
- Added 5 additional web component mapping files (file-upload, calendar, progressive, time, validation)
- Added 10 legacy component mapping files covering all 47 jQuery-based components
- Total coverage expanded from 48 to 93 MCA1 components
- Extended table mapping with 6 additional table variant patterns

### v4.0 (April 24, 2026) - 6 NEW COMPONENTS + 5 ENRICHED MAPPINGS
- Added 6 new mapping files: Tabs, StatusBar, Spinner, Image, Popover, Stepper
- Enriched 5 existing mapping files: Icon, Data Display, Form Controls, Layout, Dialog
- Updated `<mca-image>` from `<img>` to `<Multimedia>` component
- Updated `<mca-modal>` to include Modal ref-based API alternative alongside Dialog
- Component inventory expanded from 42 to 48 entries
- All new mappings include complete TypeScript props from blueprint-react source

### v3.0 (April 16, 2026) - SPLIT INTO PER-COMPONENT FILES
- Split monolithic file into 14 individual mapping files in `mappings/` directory
- Each component has its own self-contained file with before/after examples and attribute mapping tables
- This file now serves as the index linking to all component mapping files
- Complete component inventory table updated with links to individual files
- No content was removed; all mappings preserved in their respective files

### v2.4 (April 16, 2026) - COMPREHENSIVE `<mca-notify>` MAPPING
### v2.3 (April 16, 2026) - COMPREHENSIVE `<mca-checkboxes>` / `<mca-checkbox>` MAPPING
### v2.2 (April 16, 2026) - COMPREHENSIVE `<mca-textarea>` MAPPING
### v2.1 (April 16, 2026) - COMPREHENSIVE `<mca-input>` MAPPING
### v2.0 (April 16, 2026) - COMPLETE REWRITE
### v1.0 (Initial)
