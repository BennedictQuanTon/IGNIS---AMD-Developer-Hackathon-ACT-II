# IGNIS frontend

Landing page and workspace design preview for [issue #19](https://github.com/khanhtuongnakitomo/IGNIS/issues/19). This code follows [DESIGN.md](../docs/design/DESIGN.md) and [LANDING_PAGE.md](../docs/design/LANDING_PAGE.md).

**Local implementation:** `#/app` uses the Python workflow API through the `/api` dev/preview proxy. Runs, decisions, revisions, evidence and issued PDFs come from backend persistence. The embedded landing-page preview still uses explicitly labelled mock data. The API-connected implementation needs the browser and manual checks in the [local E2E guide](../docs/LOCAL_RUN.md); it is not a claimed deployed E2E pass.

**Stack:** React 19, TypeScript, Vite 7, Tailwind CSS v4, `motion` for animation and `simple-icons` (bundled SVG paths) for the tech-stack logos. It uses system fonts only; other icons and charts are inline SVG. Confirm this stack with the backend owner before integrating.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (landing); add #/app for the workspace
npm run build      # typecheck + production build into frontend/dist
npm run test:e2e:list # typecheck/discover browser cases without executing them
npm run test:e2e    # isolated replay API + browser tests on ports 8776/5178
```

## Layout

- `src/content/site.ts`: all landing copy and figures, each with its source. To add the product screenshot, set `productScreenshot`. To show the demo button, set `demoUrl`.
- `src/components/landing/`: Nav, Hero (evidence-trace animation), Story (challenge, track, product flow, features) and Proof (frame, delivered metrics, comparison, team, sources, footer).
- `src/components/ui/`: tokens-based primitives, motion helpers (`Reveal`, `Stagger`, `CountUp`) and icons.
- `src/workspace/connected/`: typed API client, revision-aware state, six connected stages and evidence inspector.
- `src/workspace/Workspace.tsx`, `screens.tsx`, `Inspector.tsx`, `mock.ts`: wrapper plus the original embedded design preview.

`VITE_API_BASE` defaults to `/api`; `IGNIS_API_PROXY` defaults to `http://127.0.0.1:8765`. AMD keys belong only to the Python process. The Vite proxy handles local development and preview; a production static deployment needs its own same-origin reverse proxy or an explicitly configured backend origin. No live inference is requested automatically.

Motion respects `prefers-reduced-motion`. Benchmark figures stay *Pending measurement* until issue #18 publishes real results.
