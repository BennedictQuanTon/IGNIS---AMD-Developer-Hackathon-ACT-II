import { expect, test, type Locator, type Page } from "@playwright/test";
import type { Run } from "../src/workspace/connected/api";

async function saved(page: Page, button: Locator) {
  const [response] = await Promise.all([page.waitForResponse(value => value.request().method() === "POST" && value.url().includes("/api/runs")), button.click()]);
  expect(response.status(), await response.text()).toBeLessThan(400);
  await expect(page.getByRole("status")).toBeEmpty();
}
async function stage(page: Page, name: string) {
  await page.getByRole("navigation", { name: "Workflow stages" }).getByRole("button", { name: new RegExp(name) }).click();
}
async function current(page: Page): Promise<Run> {
  const id = await page.getByLabel("Saved runs").inputValue();
  const response = await page.request.get(`/api/runs/${id}`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}
async function analyzed(page: Page) {
  await page.goto("/#/app");
  await page.getByRole("button", { name: "Load recorded demo input", exact: true }).click();
  await expect(page.getByRole("button", { name: "Confirm mapping", exact: true })).toBeVisible();
  await saved(page, page.getByRole("button", { name: "Confirm mapping", exact: true }));
  await page.getByRole("button", { name: "Continue to review", exact: true }).click();
  await saved(page, page.getByRole("button", { name: "Start extraction", exact: true }));
  const decisions = page.getByRole("button", { name: "Save record decision", exact: true });
  await expect(decisions).toHaveCount(6);
  for (let index = 0; index < 6; index++) await saved(page, decisions.nth(index));
  await page.getByRole("button", { name: "Continue to facts", exact: true }).click();
  await saved(page, page.getByRole("button", { name: "Analyze approved records", exact: true }));
  const run = await current(page);
  expect(run.stage_status.review).toBe("succeeded");
  expect(run.snapshot?.entries).toHaveLength(5);
  return run;
}
async function explained(page: Page) {
  await analyzed(page);
  await page.getByRole("button", { name: "Continue to evidence", exact: true }).click();
  await saved(page, page.getByRole("button", { name: "Retrieve evidence", exact: true }));
  await saved(page, page.getByRole("button", { name: "Generate explanation", exact: true }));
  expect((await current(page)).draft_result?.status).toBe("pending_expert_review");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(await page.evaluate(() => window.innerWidth));
}
async function issued(page: Page) {
  await explained(page);
  await page.getByRole("textbox", { name: "Expert review reason", exact: true }).fill("Replay E2E: simulated signoff, not a real expert approval");
  await saved(page, page.getByRole("button", { name: "Save expert review", exact: true }));
  expect((await current(page)).stage_status.context).toBe("accepted");
  await page.getByRole("button", { name: "Continue to report", exact: true }).click();
  await saved(page, page.getByRole("button", { name: "Issue approved PDF", exact: true }));
  return current(page);
}

test("@replay full browser journey persists and downloads the actual issued PDF", async ({ page }, info) => {
  const errors: string[] = [], authHeaders: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => { if (request.headers().authorization) authHeaders.push(request.url()); });
  const run = await issued(page);
  const report = run.latest_report!;
  await expect(page.getByRole("link", { name: "Download current PDF", exact: true })).toHaveAttribute("href", `/api/runs/${run.run_id}/report/${report.report_id}`);
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Download current PDF", exact: true }).click()]);
  await download.saveAs(info.outputPath("issued-report.pdf"));
  await page.reload();
  await expect(page.getByLabel("Saved runs")).toHaveValue(run.run_id);
  await stage(page, "Report");
  await expect(page.getByRole("link", { name: "Download current PDF", exact: true })).toBeVisible();
  await stage(page, "Facts");
  await page.getByRole("button", { name: run.facts[0].fact_id, exact: true }).click();
  const inspector = page.getByRole("dialog", { name: "Evidence inspector" });
  await expect(inspector).toContainText(run.facts[0].fact_id);
  await page.keyboard.press("Escape");
  await expect(inspector).not.toBeVisible();
  expect(errors).toEqual([]); expect(authHeaders).toEqual([]);
  await info.attach("replay-identity", { body: JSON.stringify({ commit: process.env.IGNIS_TEST_COMMIT || "local working tree; inspect git diff", run_id: run.run_id, revision: run.revision, snapshot: run.snapshot?.snapshot_id, mode: "hosted_replay", synthetic: true, simulated_signoff: true, live_calls: 0 }), contentType: "application/json" });
  await info.attach("connected-workspace", { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
});

test("@replay correction invalidates downstream state and preserves the old issued PDF", async ({ page }) => {
  const original = await issued(page);
  await stage(page, "Review");
  await page.getByLabel(/Use recorded-demo decisions/).uncheck();
  const panel = page.locator("section").filter({ has: page.getByRole("heading", { name: new RegExp(`^Row ${original.records[0].locator.row} ·`) }) });
  await panel.getByRole("combobox", { name: "Record decision", exact: true }).selectOption("corrected");
  await panel.getByRole("textbox", { name: "Record decision reason", exact: true }).fill("Source annotation corrected during E2E");
  await saved(page, panel.getByRole("button", { name: "Save record decision", exact: true }));
  const corrected = await current(page);
  expect(corrected.snapshot).toBeNull(); expect(corrected.expert_reviews).toEqual([]); expect(corrected.latest_report).toBeNull();
  await stage(page, "Report");
  await expect(page.getByRole("button", { name: "Issue approved PDF", exact: true })).toBeDisabled();
  await expect(page.getByRole("link", { name: "Download current PDF", exact: true })).toHaveCount(0);
  const oldPdf = await page.request.get(`/api/runs/${original.run_id}/report/${original.latest_report!.report_id}`);
  expect(oldPdf.ok()).toBeTruthy(); expect((await oldPdf.body()).subarray(0, 4).toString()).toBe("%PDF");
});

test("@replay rejected and inconclusive findings cannot issue a report", async ({ page }) => {
  await explained(page);
  for (const outcome of ["rejected", "inconclusive"]) {
    await page.getByRole("combobox", { name: "Expert decision", exact: true }).selectOption(outcome);
    await page.getByRole("textbox", { name: "Expert review reason", exact: true }).fill(`E2E ${outcome} decision`);
    await saved(page, page.getByRole("button", { name: "Save expert review", exact: true }));
    expect((await current(page)).stage_status.context).toBe(outcome);
    await stage(page, "Report");
    await expect(page.getByRole("button", { name: "Issue approved PDF", exact: true })).toBeDisabled();
    await stage(page, "Evidence");
  }
});

test("@mock-boundary 429 and timeout keep saved facts readable without retry storms", async ({ page }) => {
  const run = await analyzed(page);
  await stage(page, "Evidence");
  await saved(page, page.getByRole("button", { name: "Retrieve evidence", exact: true }));
  let calls = 0;
  await page.route("**/api/runs/*/context/generate", async route => { calls++; await route.fulfill({ status: 429, headers: { "Content-Type": "application/json", "Retry-After": "1" }, body: JSON.stringify({ error: "rate_limited", message: "Shared quota busy" }) }); });
  await page.getByRole("button", { name: "Generate explanation", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Shared quota busy");
  await expect(page.getByRole("button", { name: "Generate explanation", exact: true })).toBeEnabled();
  expect(calls).toBe(1);
  await page.unroute("**/api/runs/*/context/generate");
  await page.route("**/api/runs/*/context/generate", route => route.abort("timedout"));
  await page.getByRole("button", { name: "Generate explanation", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("server may still be processing");
  await stage(page, "Facts");
  await expect(page.getByRole("button", { name: run.facts[0].fact_id, exact: true })).toBeVisible();
});

test("@mock-boundary stale revision refreshes state and does not repeat the mutation", async ({ page }) => {
  await page.goto("/#/app");
  await page.getByRole("button", { name: "Load recorded demo input", exact: true }).click();
  await expect(page.getByRole("button", { name: "Confirm mapping", exact: true })).toBeVisible();
  let calls = 0;
  await page.route("**/api/runs/*/mapping/confirm", async route => { calls++; await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ error: "revision_conflict" }) }); });
  await page.getByRole("button", { name: "Confirm mapping", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("inspect it before retrying");
  expect(calls).toBe(1); expect((await current(page)).mapping).toBeNull();
});
