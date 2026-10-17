export type Json = Record<string, unknown>;
export type Extraction = { entities: { id: string; type: string; text: string; start: number; end: number }[]; relations: Json[] };
export type RecordRow = { record_id: string; text: string; text_norm: string; locator: { row: number; sheet?: string }; asset_id: string | null; work_order_id: string | null };
export type Suggestion = { record_id: string; model_id: string; model_version: string; adapter_mode: string; status: string; output: Extraction | null; errors: string[] };
export type Decision = { status: string; reason: string; reviewer: string; revision: number; output: Extraction | null };
export type Fact = { fact_id: string; kind: string; scope: Record<string, string>; value: number | null; unit: string; status: string; reason?: string; record_ids: string[]; input_fact_ids: string[] };
export type Passage = { passage_id: string; document_id: string; version: string; source_id: string; location: string; text: string; reader?: Json; [key: string]: unknown };
export type Claim = { text: string; citations: string[]; fact_bindings: Json[] };
export type Draft = { pack_id: string; hypotheses: Claim[]; alternatives: Claim[]; uncertainty: string; inspection: Claim | null; abstain: boolean };
export type Pack = { pack_id: string; snapshot_id: string; asset_id: string; component: string; synthetic: boolean; corpus_version: string; graph_version: string; facts: Fact[]; passages: Passage[] };
export type Report = { report_id: string; snapshot_id: string; sha256: string; synthetic: boolean; expert_review: { decision: string; reviewer: string }; [key: string]: unknown };
export type Run = {
  run_id: string; revision: number; status: string; name: string; operator: string; synthetic: boolean; adapter_mode: string;
  filename?: string; source_sha256?: string; row_count?: number; columns?: string[]; raw_rows?: { locator: Json; values: Record<string, string> }[];
  row_issues?: string[]; criticalities?: { component: string; value: number; reason: string; set_by: string }[]; proposal?: { mapping: Record<string, string | null>; evidence: Record<string, string> };
  mapping: Json | null; records: RecordRow[]; suggestions: Suggestion[]; decisions: Record<string, Decision>;
  snapshot: { snapshot_id: string; entries: { record: RecordRow; projection: Json }[] } | null;
  facts: Fact[]; alerts: Json[]; stage_status: Record<string, string>; stage_errors?: string[];
  extraction_identity?: { model_id: string; model_version: string; configuration: string };
  context: { status: string; reason?: string; corpus_mode?: string; pack: Pack | null; trace?: Json } | null;
  draft_result?: { status: string; errors: string[]; draft: Draft | null; model_id?: string; prompt_id?: string; explanation_mode: string } | null;
  expert_reviews: { decision: string; reason: string; reviewer: string; [key: string]: unknown }[];
  latest_report?: Report | null; report_ids: string[];
};
export type Health = { status: string; extraction_mode: string; extraction_model: string; explanation_mode: string; explanation_model: string; explanation_prompt: string; corpus_mode: string; demo_input_available: boolean };
export type DemoInput = { filename: string; csv_text: string; synthetic: boolean; name: string; operator: string };
export type History = { revision: number; kind: string; data: Json }[];

const BASE = (import.meta.env.VITE_API_BASE || "/api").replace(/\/$/, "");
export class ApiError extends Error {
  constructor(message: string, public status: number, public payload: Json, public retryAfter: number) { super(message); }
}
export async function request<T>(path: string, body?: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 300_000);
  try {
    const response = await fetch(BASE + path, { method: body === undefined ? "GET" : "POST", signal: controller.signal,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
    const payload = await response.json();
    if (!response.ok) {
      const retry = response.headers.get("Retry-After");
      const seconds = retry ? (/^\d+$/.test(retry) ? Number(retry) : Math.max(0, (Date.parse(retry) - Date.now()) / 1000)) : 60;
      throw new ApiError(payload.message || payload.error || `Request failed (${response.status})`, response.status, payload, Number.isFinite(seconds) ? seconds : 60);
    }
    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new Error("Connection interrupted or timed out. The server may still be processing. Refresh the run before retrying; your saved data remains available.");
  } finally { window.clearTimeout(timeout); }
}
export function reportUrl(runId: string, reportId: string) {
  return `${BASE}/runs/${encodeURIComponent(runId)}/report/${encodeURIComponent(reportId)}`;
}
export async function filePayload(file: File) {
  if (file.size > 5_500_000) throw new Error("Choose a file below 5.5 MB to fit the API upload limit.");
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let start = 0; start < bytes.length; start += 32_768) binary += String.fromCharCode(...bytes.subarray(start, start + 32_768));
  return { filename: file.name, content_base64: btoa(binary) };
}
