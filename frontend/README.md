# IGNIS frontend

Landing page and workspace design preview for [issue #19](https://github.com/khanhtuongnakitomo/IGNIS/issues/19). This code follows [DESIGN.md](../docs/design/DESIGN.md) and [LANDING_PAGE.md](../docs/design/LANDING_PAGE.md).

**Status:** the workspace at `#/app` runs on synthetic mock data and is labelled that way on screen. It is not connected to a backend or the AMD API. Review decisions stay in the browser tab and reset on reload.

**Stack:** React 19, TypeScript, Vite 7, Tailwind CSS v4, `motion` for animation and `simple-icons` (bundled SVG paths) for the tech-stack logos. It uses system fonts only; other icons and charts are inline SVG. Confirm this stack with the backend owner before integrating.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (landing); add #/app for the workspace
npm run build      # typecheck + production build into frontend/dist
```

## Layout

- `src/content/site.ts`: all landing copy and figures, each with its source. To add the product screenshot, set `productScreenshot`. To show the demo button, set `demoUrl`.
- `src/components/landing/`: Nav, Hero (evidence-trace animation), Story (challenge, track, product flow, features) and Proof (frame, delivered metrics, comparison, team, sources, footer).
- `src/components/ui/`: tokens-based primitives, motion helpers (`Reveal`, `Stagger`, `CountUp`) and icons.
- `src/workspace/`: shell, six stage screens, inspector and mock fixtures (`mock.ts`).

Motion respects `prefers-reduced-motion`. Benchmark figures stay *Pending measurement* until issue #18 publishes real results.
