# BDL Image to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Image (`<mca-image>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-image>` | `<Multimedia>` |

**Note**: This mapping supersedes the `<mca-image>` to `<img>` mapping referenced in [BDL_ICON_MAPPING.md](BDL_ICON_MAPPING.md). The `<Multimedia>` component is the correct Blueprint-React replacement for `<mca-image>`, providing built-in aspect ratio control, responsive image support, and border radius options. Do NOT map `<mca-image>` to a plain `<img>` tag — always use `<Multimedia>`.

---

### Basic Image

**MCA1 (Before)**:
```html
<mca-image
  src=""
  zoomsrc=""
  title=""
  alt=""
  id=""
  class=""
  width=""
  height=""
  align="left"
>
</mca-image>
```

**Blueprint-React (After)**:
```typescript
<Multimedia
  alt="Placeholder image"
  src="https://blueprint.np3.apaas4.barclays.intranet/latest/react/assets/16x9-light-BoC-guep.jpg"
  width="300px"
/>
```

### Image Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Notes |
|---|---|---|
| `src` | `src` | Image URL |
| `alt` | `alt` | Alternative text (required for accessibility) |
| `title` | `title` | Native HTML title (browser hover text) |
| `id` | `id` | Element identifier |
| `class` | `className` | React convention |
| `width` | `width` | CSS width (e.g., "300px", "100%") |
| `height` | `height` | CSS height (e.g., "200px", "auto") |
| `align="left"` / `align="right"` | Use parent layout (`<Arrange>`) | Not a direct Multimedia prop |
| `zoomsrc` | N/A | Zoom functionality not directly supported; use lightbox library if needed |

### Image with Layout Control

**MCA1 (Before)**:
```html
<mca-fluidview>
  <mca-cell grow="10">
    <mca-image align="right" src="/path/to/image.jpg" alt="Description"></mca-image>
  </mca-cell>
</mca-fluidview>
```

**Blueprint-React (After)**:
```typescript
<Arrange justify="end">
  <ArrangeItem size="fit">
    <Multimedia alt="Description" src="/path/to/image.jpg" width="300px" />
  </ArrangeItem>
</Arrange>
```

---

### Basic Image (Simpler)

**MCA1 (Before)**:
```html
<mca-image id="img_basic" src="/images/photo.jpg" alt="A sample photo" title="Sample Photo">
</mca-image>
```

**Blueprint-React (After)**:
```typescript
<Multimedia
  id="img_basic"
  src="/images/photo.jpg"
  alt="A sample photo"
  title="Sample Photo"
/>
```

---

### Image with Dimensions (Width / Height)

MCA1's `<mca-image>` supports `width` and `height` attributes. Blueprint-React's `<Multimedia>` inherits all standard `<img>` props, so `width` and `height` are passed directly.

**MCA1 (Before)**:
```html
<mca-image id="img_sized" src="/images/banner.jpg" alt="Banner" width="600" height="200">
</mca-image>
```

**Blueprint-React (After)**:
```typescript
<Multimedia
  id="img_sized"
  src="/images/banner.jpg"
  alt="Banner"
  width={600}
  height={200}
/>
```

**Note**: In React, `width` and `height` accept numbers (pixels) or strings. Prefer numbers for pixel values.

---

### Image with Aspect Ratio

Blueprint-React's `<Multimedia>` provides a `ratio` prop that constrains the image to a predefined aspect ratio using CSS. This has no direct MCA1 equivalent — use it when migrating images that previously relied on manual CSS for aspect ratio control.

**MCA1 (Before)**:
```html
<mca-image id="img_ratio" src="/images/hero.jpg" alt="Hero image" class="custom-ratio-16x9">
</mca-image>
<!-- Aspect ratio was controlled via custom CSS class -->
```

**Blueprint-React (After)**:
```typescript
<Multimedia
  id="img_ratio"
  src="/images/hero.jpg"
  alt="Hero image"
  ratio="16x9"
  fit="cover"
/>
```

**Available `ratio` values**: `"3x4"`, `"1x1"`, `"4x3"`, `"16x9"`, `"3x1"`

**Available `fit` values**:
- `"contain"` — the image is scaled to fit within the container, preserving aspect ratio (may show letterboxing)
- `"cover"` — the image is scaled to fill the container, preserving aspect ratio (may crop edges)

---

### Responsive Image with Multimedia.Source

Blueprint-React's `<Multimedia>` supports responsive image sources via `<Multimedia.Source>`, allowing different images to be served based on viewport size. This replaces any MCA1 pattern that used JavaScript or CSS media queries to swap image sources.

**MCA1 (Before)**:
```html
<mca-image id="img_responsive" src="/images/photo-desktop.jpg" alt="Responsive photo">
</mca-image>
<!-- MCA1 relied on JS or CSS to swap between mobile/desktop images -->
```

**Blueprint-React (After)**:
```typescript
<Multimedia id="img_responsive" alt="Responsive photo" ratio="16x9" fit="cover">
  <Multimedia.Source srcSet="/images/photo-mobile.jpg" media="(max-width: 767px)" />
  <Multimedia.Source srcSet="/images/photo-tablet.jpg" media="(max-width: 1023px)" />
  <Multimedia.Source srcSet="/images/photo-desktop.jpg" media="(min-width: 1024px)" />
</Multimedia>
```

**Note**: When using `<Multimedia.Source>`, the `src` prop on `<Multimedia>` acts as the fallback image. If all sources are provided via `<Multimedia.Source>`, you may omit `src` on the parent or provide it as a default fallback.

Blueprint-React also supports responsive ratio props for different breakpoints:
- `ratioMdUp` — aspect ratio for medium screens and above (e.g., `"1x1"`)
- `ratioLgUp` — aspect ratio for large screens and above (e.g., `"3x1"`)

```typescript
<Multimedia
  id="img_responsive_ratio"
  src="/images/hero.jpg"
  alt="Hero"
  ratio="3x4"
  ratioMdUp="4x3"
  ratioLgUp="16x9"
  fit="cover"
/>
```

---

### Image with Border Radius

Blueprint-React's `<Multimedia>` supports a `radius` prop for rounding image corners. This replaces any custom CSS `border-radius` applied to `<mca-image>` in MCA1.

**MCA1 (Before)**:
```html
<mca-image id="img_rounded" src="/images/avatar.jpg" alt="User avatar" class="rounded-image">
</mca-image>
<!-- border-radius was applied via custom CSS class -->
```

**Blueprint-React (After)**:
```typescript
<Multimedia
  id="img_rounded"
  src="/images/avatar.jpg"
  alt="User avatar"
  ratio="1x1"
  radius="xl"
  fit="cover"
/>
```

**Available `radius` values**: `"none"`, `"md"`, `"lg"`, `"xl"`

---

### Zoom Functionality

MCA1's `<mca-image>` supports a `zoomsrc` attribute that provides a high-resolution image URL for a zoom/lightbox interaction, and a `rotate()` API method that toggles 180-degree rotation.

**Blueprint-React has no built-in zoom or rotate functionality.** If zoom or rotate behaviour is required, implement it using one of the following approaches:

1. **CSS Transform** — use `transform: scale(...)` and `transform: rotate(180deg)` with React state:

```typescript
const [zoomed, setZoomed] = useState(false);
const [rotated, setRotated] = useState(false);

<div
  style={{
    transform: `${zoomed ? 'scale(2)' : 'scale(1)'} ${rotated ? 'rotate(180deg)' : ''}`,
    transition: 'transform 0.3s ease',
    cursor: zoomed ? 'zoom-out' : 'zoom-in',
  }}
  onClick={() => setZoomed(!zoomed)}
>
  <Multimedia
    id="img_zoom"
    src={zoomed ? "/images/photo-highres.jpg" : "/images/photo.jpg"}
    alt="Zoomable photo"
    fit="contain"
  />
</div>
```

2. **React zoom library** — for a more complete lightbox/zoom experience, use a library such as `react-medium-image-zoom` or `react-image-lightbox`. Ensure any library is approved for use within your project's dependency policy.

**Note**: The `zoomsrc` attribute value should be preserved as the high-resolution image source. Swap `src` to the `zoomsrc` value when the user activates zoom. The `rotate()` API should be replaced with React state controlling a CSS `transform: rotate(180deg)` toggle.

---

## Complete `<mca-image>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `Multimedia` | |
| `class` | `className` | `Multimedia` | React convention |
| `src` | `src` | `Multimedia` | Image URL — inherits standard `<img>` prop |
| `alt` | `alt` | `Multimedia` | Alt text; MCA1 default was `"Image not loaded"` — provide meaningful alt text instead |
| `title` | `title` | `Multimedia` | Tooltip text — inherits standard `<img>` prop |
| `width` | `width` | `Multimedia` | Pixel or string value — inherits standard `<img>` prop |
| `height` | `height` | `Multimedia` | Pixel or string value — inherits standard `<img>` prop |
| `zoomsrc` | No direct prop | — | No built-in zoom; implement via CSS transform or React zoom library (see Zoom section above) |
| (CSS aspect ratio) | `ratio` | `Multimedia` | `"3x4"`, `"1x1"`, `"4x3"`, `"16x9"`, `"3x1"` |
| (CSS aspect ratio, responsive) | `ratioMdUp`, `ratioLgUp` | `Multimedia` | Responsive ratio for medium and large breakpoints |
| (CSS object-fit) | `fit` | `Multimedia` | `"contain"` or `"cover"` |
| (CSS border-radius) | `radius` | `Multimedia` | `"none"`, `"md"`, `"lg"`, `"xl"` |
| (responsive sources) | `<Multimedia.Source>` children | `Multimedia.Source` | `srcSet` and `media` props for responsive images |
| `rotate()` API | No direct prop | — | Implement via React state + CSS `transform: rotate(180deg)` toggle |
