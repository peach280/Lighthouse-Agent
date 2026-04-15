# Lighthouse Audit Fix Context

This file provides grounding context for each Lighthouse audit ID —
what it measures, common causes, and how to fix it in React/JSX/TSX.
Use this when generating fixes for failing audits.

---

## Aliases
When an audit is referred to by shorthand, resolve it to the canonical ID:

| Alias | Canonical audit_id |
|---|---|
| `cls` | `cumulative-layout-shift` |
| `lcp` | `largest-contentful-paint` |
| `tbt` | `total-blocking-time` |
| `fcp` | `first-contentful-paint` |
| `alt` | `image-alt` |
| `contrast` | `color-contrast` |
| `title` | `document-title` |
| `lang` | `html-lang` |
| `description` | `meta-description` |

---

## Performance

### `cumulative-layout-shift`
CLS measures unexpected layout shifts during page load.

**Common causes:**
- Images/videos without explicit `width` + `height`
- Dynamically injected content above existing content
- Web fonts causing text reflow (FOIT/FOUT)

**Fix goal:** Reserve space before content loads so nothing shifts.

**Example fix:**
```tsx
// BEFORE — no dimensions, causes layout shift
<img src="hero.jpg" className="banner" />

// AFTER — explicit dimensions reserve space
<img src="hero.jpg" className="banner" width={1200} height={600} />
```

---

### `largest-contentful-paint`
LCP measures when the largest above-the-fold element finishes rendering.

**Common causes:**
- Lazy-loaded LCP image
- No preload hint for the LCP resource
- Render-blocking scripts or stylesheets
- Slow server TTFB

**Fix goal:** Fetch the LCP resource as early as possible.

**Example fix:**
```html
<!-- Add preload hint in <head> -->
<link rel="preload" as="image" href="/hero.jpg" />
```

---

### `total-blocking-time`
TBT measures main-thread blocking time between FCP and TTI.

**Common causes:**
- Large JS bundles parsed synchronously
- Long tasks > 50ms on the main thread
- Synchronous third-party scripts

**Fix goal:** Break up long tasks or defer non-critical scripts.

**Example fix:**
```html
<!-- BEFORE -->
<script src="heavy-library.js"></script>

<!-- AFTER -->
<script src="heavy-library.js" defer></script>
```

---

## Accessibility

### `image-alt`
Every `<img>` element must have an `alt` attribute.

**Rules:**
- Decorative images: `alt=""`
- Informative images: descriptive string
- In JSX the attribute is still `alt`
- Next.js `<Image>` also requires `alt`

**Example fix:**
```tsx
// BEFORE
<img src="hero.jpg" className="banner" />

// AFTER
<img src="hero.jpg" className="banner" alt="Hero banner showing dashboard overview" />
```

---

### `color-contrast`
Text must meet minimum contrast ratios:
- Normal text: **4.5:1**
- Large text / UI components: **3:1**

**Fix:** Darken text color or lighten background.
If exact color values are unknown, suggest a CSS custom property approach.

**Example fix:**
```tsx
// BEFORE — gray-500 on white fails 4.5:1
<p className="text-gray-500">Patient name</p>

// AFTER — gray-700 passes 4.5:1
<p className="text-gray-700">Patient name</p>
```

---

### `label`
Every form input needs an accessible label.

**Options:**
1. `<label htmlFor="id">` referencing the input
2. `aria-label="..."` on the input
3. `aria-labelledby="id-of-visible-text"`

Note: In React/JSX, HTML `for` becomes `htmlFor`.

**Example fix:**
```tsx
// BEFORE
<input type="text" className="input" />

// AFTER
<label htmlFor="patient-name">Patient Name</label>
<input id="patient-name" type="text" className="input" />
```

---

### `button-name`
Buttons must have an accessible name via:
- Visible text content
- `aria-label`
- `aria-labelledby`
- `title`

Icon-only buttons **always** need `aria-label`.

**Example fix:**
```tsx
// BEFORE — icon only, no accessible name
<button><SearchIcon /></button>

// AFTER
<button aria-label="Search patients"><SearchIcon /></button>
```

---

### `link-name`
Anchor elements must have discernible text.

**Options:** visible text content, `aria-label`, `aria-labelledby`, or `title`.
Icon links need `aria-label`.

**Example fix:**
```tsx
// BEFORE
<a href="/settings"><GearIcon /></a>

// AFTER
<a href="/settings" aria-label="Open settings"><GearIcon /></a>
```

---

### `html-lang`
The `<html>` element must have a `lang` attribute.

**Example fix:**
```html
<!-- BEFORE -->
<html>

<!-- AFTER -->
<html lang="en">
```

In Next.js, set it in `next.config.js`:
```js
module.exports = { i18n: { defaultLocale: 'en', locales: ['en'] } }
```

---

### `aria-required-attr`
ARIA roles require certain attributes to be present.

**Example:** `role="checkbox"` requires `aria-checked`.

**Fix:** Add the missing required ARIA attribute with an appropriate value.

```tsx
// BEFORE
<div role="checkbox">Accept terms</div>

// AFTER
<div role="checkbox" aria-checked="false">Accept terms</div>
```

---

## SEO

### `document-title`
The page must have a `<title>` in `<head>`.

**Format:** `"Page Name — Site Name"`, unique per page.

**Example fix (React):**
```tsx
import { Helmet } from 'react-helmet'

// AFTER
<Helmet><title>Dashboard — Siemens Healthineers</title></Helmet>
```

---

### `meta-description`
Add `<meta name="description" content="...">` in `<head>`.

**Rules:** 150–160 characters, unique description per page.

**Example fix:**
```tsx
<Helmet>
  <meta name="description" content="Real-time patient monitoring dashboard for ICU teams." />
</Helmet>
```