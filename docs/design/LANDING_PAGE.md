# IGNIS landing page design

**Status:** proposed spec for a single-page landing site. It is not implemented. It shares tokens, type and components with [DESIGN.md](DESIGN.md); copy the token block from there.

**Reference:** structure and restraint follow [linear.app](https://linear.app): dark canvas, large tight headline, short sections, thin borders and one accent.

## Hard rules

- **No external fonts.** Use the system stacks only (`--font-sans`, `--font-mono`), with no Google Fonts or `@font-face`.
- **No external libraries for charts or icons.** Charts are inline SVG or plain CSS bars with text values printed beside them.
- **Every number comes from the sources section below.** Benchmark results do not exist yet. Their slot shows *Pending measurement* until [issue #18](https://github.com/khanhtuongnakitomo/IGNIS/issues/18) publishes real results.
- **Write enough, never more.** Headline ≤ 8 words; section intro ≤ 2 sentences; card text ≤ 25 words.

## Page layout

Content width is 1120 px, centred, with a 24 px gutter (16 px on mobile). Sections are separated by 96 px of vertical space (64 px on mobile) and a 1 px `--border` rule. Each section opens with a small mono eyebrow label in `--text-3`, for example `01 — Challenge`.

Order:

1. Nav
2. Hero
3. The challenge
4. Track and problem
5. What IGNIS is
6. Core features
7. Product frame (image placeholder)
8. What we delivered (4 metrics)
9. Comparison
10. Team
11. Sources
12. Footer

## 1. Nav

Sticky, 56 px tall, `--bg` at 80% opacity with a 12 px backdrop blur and a bottom border.

- Left: `IGNIS` wordmark.
- Centre: links to Challenge, Product, Comparison and Team (anchor links).
- Right: a `GitHub` secondary button, plus a `View demo` primary button that stays hidden until a demo URL exists.

## 2. Hero

Centred. 160 px top padding.

- **Pill:** `AMD Developer Hackathon · ACT III · Track 1`
- **Headline (display):** **Maintenance history you can trace.**
- **Subhead (`--text-2`, max 560 px):** IGNIS turns messy maintenance work orders into human-reviewed records, code-computed priorities and cited explanations, then issues a report where every number links back to its source.
- **Buttons:** `See how it works` (primary, anchors to section 5) and `Read the proposal` (secondary, links to issue #16).
- Below the hero, a faint radial ember glow (`--accent-soft`, 600 px, centred, 40% opacity) behind the top edge of the product frame. This is the only gradient on the page.

## 3. The challenge

Eyebrow: `01 — Challenge`. Title: **AMD Developer Hackathon: ACT III**

Intro: A hybrid build event on lablab.ai, online from 12 to 18 October 2026, with an on-site final phase in Italy for selected teams. AMD technology must be part of the working product.

**Fact strip.** Four cells in a row, each a large number with a label:

| Value | Label |
|---|---|
| 7 days | Online build, 12–18 Oct 2026 |
| $17,000+ | Prize pool |
| 5 | Tracks (4 themed + Evolus) |
| 4 | Judging criteria |

**Judging criteria.** Four equal outlined chips, without scores: *Application of Technology*, *Presentation*, *Business Value* and *Originality*.

## 4. Track and problem

Eyebrow: `02 — Our track`. Title: **Track 1 · Intelligent Industry**

Quote block (left border `--accent`): "Help factories spot problems earlier and operate better." Below it: "The problem is knowing what matters and what to do next."

**Chart A: Factory data sources (coverage).** A horizontal list of the five sources named in the track brief. Each row shows a label and a status bar segment:

| Source | IGNIS status |
|---|---|
| Maintenance reports | **In scope now** (ember filled) |
| Technical manuals | **In scope now**, applicable passages only (ember filled) |
| Sensors | Roadmap (outlined) |
| Machines / logs | Roadmap (outlined) |
| Cameras | Out of scope (`--text-4`) |

Caption: *Roadmap items are designed, not built.*

**Problem cards.** Three cards, one sentence each:

1. **Messy text.** Work orders are short, inconsistent and full of equipment shorthand.
2. **Fluent but wrong.** A generated report can miscount, attach the wrong fault or cite the wrong machine's manual.
3. **No trail.** Without links back to source records, nobody can check or sign a conclusion.

## 5. What IGNIS is

Eyebrow: `03 — Product`. Title: **An evidence desk for maintenance teams**

Intro: Models propose. Code computes. People approve. Every claim in the final report resolves to a fact, a passage and an original record.

**Flow diagram.** One row of 7 small nodes joined by 1 px arrows, wrapping to 2 rows on mobile. Each node gets a mono tag for who owns it: `AI`, `CODE` or `HUMAN`.

`Upload export` (CODE) → `Extract entities` (AI) → `Review` (HUMAN) → `Facts & alerts` (CODE) → `Applicable evidence` (CODE) → `Cited draft` (AI) → `Expert sign-off → Report` (HUMAN)

The `HUMAN` tags use `--accent`, and the other two tags use `--text-3`. A legend sits beneath the diagram.

**Hospital analogy.** One line in `--text-3` with a link to the [architecture explainer](../../artifacts/ignis-architecture-explained.html): *Think of it as a hospital for machines. The model is the clerk and the drafting assistant. The maintenance expert is the responsible doctor.*

## 6. Core features

Use a 3 × 2 grid of cards (1 column on mobile). Each card has an inline-SVG line icon, a title and one sentence.

| Title | Text |
|---|---|
| Export intake | Reads CSV, XLSX and JSON exports, records file hashes and asks a person to confirm column mapping. |
| Span-level extraction | A hosted AMD model suggests components, faults and actions anchored to exact text spans. |
| Human review gate | Accept, correct or reject each record. Nothing counts until a named reviewer approves it. |
| Code-computed priority | Severity × recurrence × criticality, versioned rules. Not a failure probability. |
| Scoped evidence | An applicability graph excludes wrong-model and superseded manuals before retrieval picks the top 3 passages. |
| Checked report | Numbers render from typed facts; claims that cite nothing retrieved are rejected before the PDF. |

## 7. Product frame

Eyebrow: `04 — Inside IGNIS`. Title: **The review workspace**

- A single 16:10 frame, full content width, with `--radius-lg`, a 1 px `--border-strong` outline, `--bg-elevated` fill and a fake window bar (three 8 px `--text-4` dots).
- Placeholder: centred mono text `Product screenshot — added after integration`. Reserve the aspect ratio so the layout doesn't shift.
- Below the frame, a caption slot: `Screenshot from <commit/run id>, <LIVE|REPLAY> mode`.
- **Rule:** only real product captures go in this frame. If a mockup is used before integration, label it `Design mockup` in the caption.

## 8. What we delivered

Eyebrow: `05 — Delivered`. Title: **Built and verifiable today**

Four metric tiles in a row (2 × 2 on mobile). Each tile has a big number, a label, a one-line source and a tiny visual.

| Number | Label | Mini visual | Source |
|---|---|---|---|
| **9** | Hash-chained pipeline stages, each persisted before the next starts | 9 small squares in a row | `ignis_wo/pipeline.py`, PR #15 |
| **56** | Automated tests in the merged baseline | none | `tests/`, PR #15 |
| **1,076** | Expert-annotated MaintIE work orders, pinned by revision and SHA-256 | Stacked bar: train 860 / dev 108 / test 108 | `maintie_split_lock.json` |
| **224 · 7** | Entity types · relation types enforced by the extraction schema | none | `maintie_labels_v1.json` |

**Chart B: MaintIE split.** One horizontal stacked bar, full tile width, 12 px tall. Train is 79.9% (`--text-2`), dev is 10.0% (`--text-3`) and test is 10.0% (`--accent`). The labels print the counts. Caption: *Test answers stay out of prompts and retrieval until the configuration is frozen.*

**Benchmark slot (Chart C).** This is a wide card below the tiles, titled *Model benchmarks on AMD Token Factory*. Until issue #18 delivers measured results, it shows an empty-state row: `Extraction F1 · Schema validity · p50/p95 latency · Valid outputs/min — Pending measurement`. Once results exist, it becomes a simple horizontal bar chart per model, labelled with the model ID, sample size and test date.

## 9. Comparison

Eyebrow: `06 — Why IGNIS`. Title: **Traceable by design**

Intro: The table compares approaches by design properties, not by benchmark scores.

| Capability | Generic LLM chat | Plain RAG assistant | Spreadsheet / CMMS report | **IGNIS** |
|---|---|---|---|---|
| Numbers computed by code | – | – | ✓ | **✓** |
| Human approval before a record counts | – | – | Partial | **✓** |
| Every claim links to a source record | – | Partial | – | **✓** |
| Excludes wrong-model / superseded manuals | – | – | n/a | **✓ (in progress)** |
| Abstains when evidence is missing | – | Partial | n/a | **✓ (in progress)** |
| Labels real vs synthetic, live vs replay | – | – | – | **✓** |
| Reads free-text work orders | ✓ | ✓ | – | **✓** |

Styling:
- The IGNIS column gets an `--accent-soft` background and an accent top border.
- Use ✓ and – glyphs with `aria-label`s, and print "Partial" as text.
- Footnote: *Columns describe typical default behaviour of each approach, not specific products. "In progress" items are designed and assigned in issue #17.*

## 10. Team

Eyebrow: `07 — Team`. Title: **Team Develarper**

Three cards in a row. Each card has an initials avatar (48 px circle, `--bg-hover`, no photos unless supplied), the name, the role, the GitHub handle in mono and a one-line ownership statement.

| Name | Role | GitHub | Owns |
|---|---|---|---|
| **Khanh Tuong Huynh** | Team Lead · AI Engineer | @khanhtuongnakitomo | Backend pipeline, review data, alerts, retrieval and evidence-linked reports |
| **Long Quan Ton** | AI Engineer · Frontend Developer | @BennedictQuanTon | UI/UX, frontend, demo video and independent end-to-end evaluation |
| **Yoshio Nomura** | AI Engineer · LLMOps | @UniverseScripts | AMD API integration, MaintIE prompts and model quality/latency benchmarks |

## 11. Sources

Eyebrow: `08 — Sources`. Title: **Where every claim comes from**

A compact two-column list (one column on mobile). Each line has a mono label and a link.

- **Challenge:** [AMD Developer Hackathon ACT III, lablab.ai](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii)
- **Dataset:** [MaintIE repository (MIT)](https://github.com/nlp-tlp/maintie), pinned at revision `825e771`
- **Paper:** [MaintIE, LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.954.pdf)
- **AMD API:** [Radeon Cloud chat completions docs](https://amd-aim.github.io/radeon-cloud-docs/api/chat-completions/)
- **Proposal:** [Issue #16, API-based project proposal](https://github.com/khanhtuongnakitomo/IGNIS/issues/16)
- **Missions:** [#17 backend](https://github.com/khanhtuongnakitomo/IGNIS/issues/17) · [#18 models](https://github.com/khanhtuongnakitomo/IGNIS/issues/18) · [#19 frontend](https://github.com/khanhtuongnakitomo/IGNIS/issues/19)
- **Pipeline code:** [PR #15, deterministic work-order pipeline](https://github.com/khanhtuongnakitomo/IGNIS/pull/15)
- **Architecture:** [Proposed system workflow](../PROPOSED_SYSTEM_WORKFLOW.md)

Note: the GitHub links work once the repository is public, and making it public is a separate team decision.

## 12. Footer

Left: `IGNIS` · MIT License · *Built for AMD Developer Hackathon ACT III*. Right: a GitHub link. Add a final line in `--text-4`: *Synthetic demo data is labelled as synthetic. No factory connection, failure prediction or production savings are claimed.*

## Responsive and accessibility

- Breakpoints: 1120, 768 and 390 px. At 390 px nothing scrolls horizontally except the comparison table, which scrolls inside its own container.
- Each chart has a visible text value and a `<title>`/`aria-label`.
- Respect `prefers-reduced-motion`. The only motion on the page is a 200 ms fade-up as each section enters.
- Before publishing, re-check the challenge facts (dates, prize and rules) against the live lablab page.
