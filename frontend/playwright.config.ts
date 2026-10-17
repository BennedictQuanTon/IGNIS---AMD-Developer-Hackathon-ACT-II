import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";
import { randomUUID } from "node:crypto";

const root = resolve(import.meta.dirname, "..");
const data = resolve(root, "outputs", "browser-e2e", `${Date.now()}-${randomUUID().slice(0, 8)}`);
const uv = process.env.IGNIS_UV || "uv";
const backend = "http://127.0.0.1:8776";
const frontend = "http://127.0.0.1:5178";
export default defineConfig({
  testDir: "./e2e", fullyParallel: false, workers: 1, retries: 0, timeout: 90_000,
  expect: { timeout: 10_000 }, reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: frontend, channel: process.env.IGNIS_BROWSER_CHANNEL || (process.platform === "win32" ? "msedge" : undefined), trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop-replay", use: { ...devices["Desktop Chrome"] } },
    { name: "narrow-replay", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 }, reducedMotion: "reduce" } },
  ],
  webServer: [
    { command: `"${uv}" run --no-project --with-requirements requirements-dev.txt python -u scripts/serve_hosted.py --replay-dir docs/benchmarks/replay --port 8776 --db "${data}/state.sqlite3" --data "${data}"`, cwd: root, url: `${backend}/health`, reuseExistingServer: false, timeout: 60_000 },
    { command: "npm run dev -- --host 127.0.0.1 --port 5178 --strictPort", url: frontend, env: { IGNIS_API_PROXY: backend, VITE_API_BASE: "/api" }, reuseExistingServer: false, timeout: 60_000 },
  ],
});
