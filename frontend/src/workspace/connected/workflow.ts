import type { Fact, Run } from "./api";
export const STAGES = ["Source", "Mapping", "Review", "Facts", "Evidence", "Report"] as const;
export function stageStates(run: Run | null): string[] {
  if (!run) return ["pending", "blocked", "blocked", "blocked", "blocked", "blocked"];
  const s = run.stage_status;
  return [s.upload || "pending", s.mapping || "blocked",
    s.extraction === "failed" || s.extraction === "unavailable" ? s.extraction : s.review || "blocked",
    s.facts || "blocked", s.context || "blocked", s.report || "blocked"];
}
export function canIssue(run: Run) {
  const review = run.expert_reviews.at(-1);
  return !!run.snapshot && !!review && ["accepted", "corrected", "facts_only_approved"].includes(review.decision);
}
export function resolveReference(run: Run, id: string): { title: string; value: unknown; records: string[] } | null {
  const fact: Fact | undefined = run.facts.find(f => f.fact_id === id) || run.context?.pack?.facts.find(f => f.fact_id === id);
  if (fact) return { title: `Fact ${id}`, value: fact, records: fact.record_ids };
  const record = run.records.find(r => r.record_id === id);
  if (record) return { title: `Source row ${record.locator.row}`, value: { record, suggestion: run.suggestions.find(s => s.record_id === id), decision: run.decisions[id], source_sha256: run.source_sha256 }, records: [] };
  const passage = run.context?.pack?.passages.find(p => p.passage_id === id);
  return passage ? { title: `Evidence ${id}`, value: passage, records: [] } : null;
}
