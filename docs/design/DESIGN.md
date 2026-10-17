# IGNIS design system and workspace UI

**Status:** design for the frontend mission in [issue #19](https://github.com/khanhtuongnakitomo/IGNIS/issues/19). The local `#/app` workspace uses the workflow API, while the landing-page embedded preview retains labelled mocks. See the [local integration and test guide](../LOCAL_RUN.md); browser E2E acceptance is still a separate step. The landing page has its own spec: [LANDING_PAGE.md](LANDING_PAGE.md).

**Reference:** the visual language follows [linear.app](https://linear.app): dark, quiet, dense, precise. IGNIS takes the structure, not the brand. It uses no Linear assets, logos or copy.

## 1. Brand

| Item | Decision |
|---|---|
| Name | **IGNIS** (Latin for *fire*). Write it in capitals in the wordmark and as "IGNIS" in text |
| One-liner | Traceable maintenance work-order intelligence with checked reporting |
| Voice | Plain, exact, unhyped. State what the system computed, what the model proposed and what a person approved |
| Personality | An evidence desk, not an oracle. The calm comes from black; one yellow accent marks attention |
| Logo | Brand kit in `frontend/public/brand`: wordmark and flame-i mark (the dot of the **i** is a flame). Use the SVGs; never retype IGNIS in a font. Minimum wordmark width 72px; the flame is always `#FFC400` |

**Words to avoid:** "predicts failures", "AI-powered diagnosis", "autonomous", "real-time factory", or any savings or percentage figure that was not measured.

## 2. Hard rules

1. **No external fonts.** Do not use Google Fonts, Inter files, `@font-face` or icon fonts. Use only the system stacks below.
2. **No external UI kits or chart libraries.** Use one frontend framework, agreed with Tuong. Draw icons and charts as inline SVG. The current implementation in [frontend/](../../frontend/README.md) uses React, TypeScript, Vite, Tailwind CSS and `motion`.
3. **Show honest state only.** The UI renders backend state. It never fakes progress, approval, live data or percentages.
4. **Never use colour alone for meaning.** Every status has a text label, and an icon or shape where it helps.
5. **Keep credentials on the server.** Keys never appear in browser responses, screenshots or recordings.

## 3. Tokens

Use dark by default. A light theme comes later and reuses the same token names.

```css
:root {
  /* Surfaces: brand surface-0 (#0B0B0C) and surface-1 (#18181A), two steps between */
  --bg:            #0b0b0c;  /* page */
  --bg-elevated:   #111113;  /* sidebar, panels */
  --bg-card:       #18181a;  /* cards */
  --bg-hover:      #1f1f22;
  --border:        rgba(255,255,255,0.08);
  --border-strong: rgba(255,255,255,0.14);

  /* Ink */
  --text:          #f5f4f2;  /* primary */
  --text-2:        #d0d0d4;  /* body, leads */
  --text-3:        #a1a1a8;  /* secondary (brand ink-muted) */
  --text-4:        #6b6b72;  /* hints, mono labels */

  /* Brand yellow: a fill, one primary per screen */
  --accent:        #ffc400;
  --accent-hover:  #ffd233;
  --accent-soft:   rgba(255,196,0,0.10);
  --on-brand:      #0b0b0c;  /* text on yellow, never white */
  --brand-text:    #ffd54a;  /* yellow used as text on dark */

  /* Semantic: always paired with a text label */
  --ok:            #4cb782;  /* approved, passed */
  --warn:          #f2994a;  /* pending, stale, rate-limited */
  --danger:        #eb5757;  /* rejected, failed, invalid */
  --info:          #5e9eff;  /* live API */
  --neutral:       #a1a1a8;  /* inconclusive, replay */
  --synthetic:     #b48cff;  /* synthetic fields */

  /* Type: Linear's fallback chain without loading a web font */
  --font-sans: "SF Pro Display", -apple-system, BlinkMacSystemFont, system-ui,
               "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  --font-mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;

  --radius-sm: 4px; --radius: 8px; --radius-lg: 12px; --radius-pill: 999px;
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
}
```

Contrast: `--text` through `--text-3` on `--bg` meet WCAG AA for body text. Use `--text-4` only for non-essential hints. Yellow as text uses `--brand-text`.

**Landing type scale (measured on linear.app):** display 64/64 weight 510, tracking −0.022em; section titles 48/48 weight 510; leads 24/32; body 15/24 in `--text-3`; nav 13px; mono labels 12px uppercase in `--text-4`. Content edge sits at x=80 on a 1440px viewport.

## 4. Typography

| Role | Size / line-height | Weight | Letter-spacing |
|---|---|---|---|
| Display (landing hero only) | 56–72 / 1.05 | 600 | -0.03em |
| H1 | 32 / 1.15 | 600 | -0.02em |
| H2 | 20 / 1.3 | 600 | -0.01em |
| H3 / panel title | 15 / 1.4 | 600 | 0 |
| Body | 14 / 1.55 | 400 | 0 |
| Small / table | 13 / 1.45 | 400 | 0 |
| Label / badge | 12 / 1.3 | 500 | 0.01em |
| Mono (IDs, hashes, spans) | 12–13 / 1.45 | 400 | 0 |

Show IDs, hashes, model IDs and versions in `--font-mono`. Truncate them in the middle (`run_7f3a…c21e`) and give each a copy button.

## 5. Core components

- **Button.** Primary: `--accent` background, `#fff` text, 32 px tall, `--radius`. Secondary: transparent with a `--border-strong` outline. Ghost: text only. Use one primary button per view.
- **Badge.** 20 px pill with 12 px label, a soft tinted background (12% of the semantic colour) and a leading dot or icon.
- **Provenance badges** sit in the top bar and always show: `REAL-SOURCE TEXT` (`--text-2`), `SYNTHETIC FIELDS` (`--synthetic`), `LIVE` (`--info`) or `REPLAY` (`--neutral`), and `Model <actual id>` in mono.
- **Review state badges:** `Pending` (warn), `Approved` (ok), `Corrected` (info), `Rejected` (danger), `Inconclusive` (neutral). Information types are visually distinct: **Fact** (square icon, computed by code), **Hypothesis** (dashed outline, model draft) and **Finding** (solid outline, human-confirmed).
- **Table.** 36 px rows, 1 px `--border` row dividers, sticky header and horizontal scroll inside the table, never on the page.
- **Span highlight.** Source text uses an underline and a tinted background per type, with a text label above the span: `component`, `fault` or `action`. This stays readable without colour.
- **Inspector drawer.** Right panel, 360 px wide on desktop and a full-height labelled drawer on narrow screens. It shows the IDs, versions and source record for whatever is selected.
- **Failure panel.** Left border in `--danger` or `--warn`, plus a title, the plain reason, what is still usable, and a retry button only when the backend allows it.

## 6. Workspace shell (from issue #19)

Keep the chrome minimal: show only what changes a decision.

```text
+---------------------------------------------------------------------+
| IGNIS                                              [Mock data]       |
+------------+----------------------------------+---------------------+
| file.csv   | Current task                     | Inspector           |
| sha256…    |                                  | 360px               |
| 1 Source   |                                  |                     |
| 2 Mapping  |                                  |                     |
| 3 Review   |                                  |                     |
| ...        |                                  |                     |
+------------+----------------------------------+---------------------+
```

- **Top bar:** wordmark plus provenance badges that are true and meaningful for the current run: `Mock data`, `Replay`, `Live` with the actual model ID, or `Synthetic fields`. Never show a placeholder badge such as "Model —".
- **Sidebar (240 px):** the source file and hash, then the six stages with a status icon (done, to do, blocked). Below 1024 px the sidebar is replaced by a horizontal stepper.
- **No status bar.** API, rate-limit and missing-context problems appear as a failure panel in the stage where they happen.
- Below 1280 px the inspector becomes a drawer. At 390 px tables scroll inside their container.

## 7. Screens

Each screen uses placeholder values until the backend supplies them. No screen ships a fixture number as a real result.

| # | Screen | Main content | Primary action | Must show |
|---|---|---|---|---|
| 1 | Source | File upload; file name, hash, parser and row counts; unmodified preview rows | Choose file | Row validation issues; real/synthetic provenance |
| 2 | Mapping | Source column → canonical field table with a validation column | Confirm mapping | A heuristic match is labelled *Proposed* until confirmed; confirming records the reviewer |
| 3 | Annotation review | Counts per state; original text with spans; suggestion list; review history | Save decision → Next pending | Accept / Correct / Reject with a reason; invalid model output shown as invalid; manual annotation when AI fails |
| 4 | Facts & alerts | Component table: severity, recurrence, criticality, priority, band, with rule version and fact IDs; alert card | Investigate evidence | "Priority is a historical rule-based ordering, not a failure chance." Missing KPIs say *Not computed – reason* |
| 5 | Evidence & expert review | Trusted facts beside applicable passages; excluded sources with reasons; the AI draft, an abstention or *Unavailable* | Save expert decision | Accept / Correct / Reject / Inconclusive; maintenance authorisation is a separate action |
| 6 | Report | Draft, Approved or Failed status; claim → fact/passage → record links; output history | Generate approved report | Only actions the backend permits; a failure never links an older PDF as new |

## 8. States every screen designs for

Every screen needs a design for each of these: loading (skeleton rows, no spinner percentages), empty, pending, invalid output, stale revision (conflict dialog showing *yours* versus *latest*), offline, `429` rate-limited (show the backend retry time and disable repeated clicks), context unavailable (facts and alerts stay visible), and provider outage.

## 9. Motion and sound

- Animate opacity and translate (4–8 px) only, using `--dur` and `--ease`. Avoid bounce and parallax.
- Respect `prefers-reduced-motion`. When it is set, transitions become instant.
- Product sounds are optional, off by default and mutable. They never carry information on their own.

## 10. Accessibility checklist

- Every control is reachable by keyboard, and focus shows as a 2 px `--accent` outline with a 2 px offset.
- Every input has a label. Errors are announced (`aria-live="polite"`) and placed beside the field.
- No information depends on hover alone.
- Inspect layouts at desktop width and at 390 px.

## 11. Don't

Don't use fake moving sensor charts, risk percentages, "trained model" badges, savings claims or glassmorphism, or more than one accent colour per view. Don't silently show replay as live.
