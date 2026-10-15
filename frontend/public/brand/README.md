# IGNIS brand

Yellow and black, themed on fire. The mark is an **i** whose dot is a flame — a torch: IGNIS lights up what is happening inside the machine.

## Logo

| File | Use |
|---|---|
| `logo/svg/ignis-lockup.svg` | Main logo on light backgrounds |
| `logo/svg/ignis-lockup-reverse.svg` | Main logo on dark backgrounds |
| `logo/svg/ignis-wordmark(-reverse).svg` | Wordmark only (headers, PDF reports) |
| `logo/svg/ignis-app-icon.svg` | App icon, avatar, social |
| `logo/svg/ignis-mark(-reverse).svg` | Flame-i alone, under 32px tall |
| `logo/favicon.ico`, `logo/png/ignis-app-icon-{16..512}.png` | Favicon, PWA / apple-touch icons |
| `logo/png/*-1200w.png`, `*-512.png` | Slides, README banners, docs (transparent PNG) |

Rules: clear space on every side = the flame's height. Minimum wordmark width 72px. The flame is always `#FFC400` (all-black only on the yellow tile). Do not recolor the bar, round the letters, stretch, rotate, or type "IGNIS" in a font in place of the wordmark.

## Color

| Token | Dark (default) | Light | Use |
|---|---|---|---|
| `brand-yellow` | `#FFC400` | `#FFC400` | Flame, primary button fill — one per screen |
| `on-brand` | `#0B0B0C` | `#0B0B0C` | Text on yellow |
| `brand-text` | `#FFD54A` | `#8A6100` | Yellow as text (links, active labels) |
| `surface-0` | `#0B0B0C` | `#FAFAF9` | Page background |
| `surface-1` | `#18181A` | `#FFFFFF` | Cards, panels |
| `line` | `#2E2E32` | `#E4E2DF` | Dividers |
| `ink` | `#F5F4F2` | `#0B0B0C` | Primary text |
| `ink-muted` | `#A1A1A8` | `#5C5C63` | Secondary text |

Never put text in `brand-yellow` on a light background (1.6:1) — use `brand-text`.

## Use in code

```html
<link rel="icon" href="/brand/logo/favicon.ico">
<link rel="apple-touch-icon" href="/brand/logo/png/ignis-app-icon-180.png">
<link rel="stylesheet" href="/brand/tokens/tokens.css">
```

```css
body { background: var(--ignis-surface-0); color: var(--ignis-ink); }
.btn-primary { background: var(--ignis-brand-yellow); color: var(--ignis-on-brand); }
```

Theme follows the OS; force it with `<html data-theme="light">` or `"dark"`. Tailwind: add `tokens/tailwind.preset.js` to `presets`, then use `bg-ignis-surface-0`, `text-ignis-ink`, `bg-ignis-brand-yellow`.
