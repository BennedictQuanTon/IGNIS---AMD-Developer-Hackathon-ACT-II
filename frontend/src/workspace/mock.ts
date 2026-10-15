// Mock fixtures for the workspace design preview. Everything here is synthetic and is
// replaced by backend responses once the contract with issue #17 is frozen.

export type SpanType = "component" | "fault" | "action";
export type Span = { start: number; end: number; type: SpanType };
export type RecordState = "pending" | "approved" | "corrected" | "rejected";

export type WorkOrder = {
  id: string;
  row: number;
  asset: string;
  text: string;
  spans: Span[];
  invalidOutput?: string;
};

function spans(text: string, parts: [string, SpanType][]): Span[] {
  let cursor = 0;
  return parts.map(([word, type]) => {
    const start = text.indexOf(word, cursor);
    if (start < 0) throw new Error(`span "${word}" not in "${text}"`);
    cursor = start + word.length;
    return { start, end: start + word.length, type };
  });
}

function wo(id: string, row: number, asset: string, text: string, parts: [string, SpanType][], invalid?: string): WorkOrder {
  return { id, row, asset, text, spans: invalid ? [] : spans(text, parts), invalidOutput: invalid };
}

export const run = {
  id: "run_mock_7f3a1c21e",
  file: "pump_history_demo.csv",
  hash: "sha256:9c1e…a04f",
  parser: "csv-v1",
  rows: 6,
  issues: 1,
};

export const columns = [
  { source: "Work Description", target: "work-order text", rule: "required", proposed: true, sample: "pump P-101 seal leaking…" },
  { source: "Equipment", target: "asset ID", rule: "synthetic origin", proposed: true, sample: "P-101" },
  { source: "Date Raised", target: "raised date", rule: "ISO date", proposed: true, sample: "2026-03-14" },
  { source: "Downtime (h)", target: "downtime hours", rule: "finite ≥ 0", proposed: true, sample: "4.5" },
];

export const rowIssues = [{ row: 5, column: "Downtime (h)", message: "Value “-3” is negative; kept as not computed." }];

export const records: WorkOrder[] = [
  wo("WO-0418", 1, "P-101", "pump P-101 seal leaking, replaced seal and gasket", [
    ["seal", "component"],
    ["leaking", "fault"],
    ["replaced", "action"],
  ]),
  wo("WO-0422", 2, "P-101", "bearing noisy on motor drive end", [
    ["bearing", "component"],
    ["noisy", "fault"],
  ]),
  wo("WO-0431", 3, "P-101", "replace worn impeller on P-101", [
    ["replace", "action"],
    ["worn", "fault"],
    ["impeller", "component"],
  ]),
  wo("WO-0440", 4, "P-102", "coupling misaligned, realigned coupling", [
    ["coupling", "component"],
    ["misaligned", "fault"],
    ["realigned", "action"],
  ]),
  wo("WO-0447", 5, "P-102", "motor overheating, check cooling fan", [
    ["motor", "component"],
    ["overheating", "fault"],
    ["check", "action"],
    ["cooling fan", "component"],
  ]),
  wo("WO-0452", 6, "P-101", "seal leak again on P-101 drive end", [], "Model output failed schema check: span offset outside text."),
];

export const facts = [
  { id: "F-01", component: "seal · P-101", severity: 3, recurrence: 2, criticality: "A", priority: 6, band: "High" },
  { id: "F-02", component: "impeller · P-101", severity: 2, recurrence: 1, criticality: "A", priority: 2, band: "Medium" },
  { id: "F-03", component: "coupling · P-102", severity: 2, recurrence: 1, criticality: "B", priority: 1, band: "Low" },
  { id: "F-04", component: "motor · P-102", severity: null, recurrence: 1, criticality: "B", priority: null, band: null },
];

export const alert = {
  id: "ALT-01",
  kind: "initial notice",
  component: "seal · P-101",
  rule: "High band on first snapshot (initial notice, not a crossing)",
  snapshot: "snap_mock_02",
};

export const passages = [
  {
    id: "P-01",
    source: "PX-100 manual rev B · §4.2",
    text: "Mechanical seal: when leakage recurs, inspect seal faces for scoring and check flush line flow.",
    path: "P-101 → seal → PX-100 manual rev B",
  },
  {
    id: "P-02",
    source: "Reviewed case C-12",
    text: "Repeated seal leakage traced to dry running after an incorrect priming step.",
    path: "P-101 → seal → case C-12",
  },
];

export const excluded = [
  { source: "PX-200 manual · §3.1", reason: "Model mismatch: P-101 is a PX-100" },
  { source: "PX-100 manual rev A · §4.2", reason: "Superseded by rev B" },
  { source: "Draft case C-15", reason: "Not yet approved" },
];

export const draft = {
  status: "AI DRAFT" as const,
  hypothesis: "Recurring seal leakage on P-101 is consistent with seal-face wear [P-01]; a reviewed case links similar leakage to dry running [P-02].",
  facts: ["F-01"],
  passages: ["P-01", "P-02"],
  alternatives: ["Installation error during the previous seal replacement"],
  uncertainty: "No operating data about dry running is available in this evidence pack.",
  inspection: "Inspect seal faces and confirm the priming procedure.",
  checks: ["Schema valid", "All cited IDs are in the evidence pack", "No numbers outside typed facts", "Snapshot matches"],
};

export const claims = [
  { text: "Seal on P-101 has the highest priority in this snapshot.", refs: ["F-01"] },
  { text: "Seal leakage on P-101 recurs in the approved snapshot.", refs: ["F-01", "WO-0418"] },
  { text: "Expert-reviewed finding: leakage consistent with seal-face wear.", refs: ["P-01", "P-02"] },
];
