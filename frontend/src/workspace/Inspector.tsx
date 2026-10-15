import { AnimatePresence, motion } from "motion/react";
import { EASE } from "../components/ui/motion";
import { Badge } from "../components/ui/primitives";
import { columns, facts, passages, records, run } from "./mock";
import type { Selection } from "./screens";
import type { Decision } from "./Workspace";

function Row({ k, v, mono = true }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="grid grid-cols-[96px_1fr] gap-2 border-b border-line py-2 text-[12px] last:border-0">
      <dt className="text-fg-4">{k}</dt>
      <dd className={mono ? "font-mono break-all text-fg-2" : "text-fg-2"}>{v}</dd>
    </div>
  );
}

function resolve(selection: NonNullable<Selection>, decisions: Record<string, Decision>) {
  const id = selection.id;
  const record = records.find((r) => r.id === id);
  if (record) {
    const d = decisions[record.id];
    return {
      title: `Record ${record.id}`,
      tag: "Source record",
      rows: [
        ["Text", record.text],
        ["Source row", `${run.file} · row ${record.row}`],
        ["File hash", run.hash],
        ["Asset", `${record.asset} (synthetic)`],
        ["Review", `${d.state} · rev ${d.revision}`],
      ],
    };
  }
  const fact = facts.find((f) => f.id === id);
  if (fact)
    return {
      title: `Fact ${fact.id}`,
      tag: "Computed by code",
      rows: [
        ["Component", fact.component],
        ["Priority", fact.priority === null ? "not computed" : String(fact.priority)],
        ["Rule", "severity_v1 × triage_v1"],
        ["Snapshot", "snap_mock_02"],
        ["Inputs", "WO-0418 (approved)"],
      ],
    };
  const passage = passages.find((p) => p.id === id);
  if (passage)
    return {
      title: `Passage ${passage.id}`,
      tag: "Retrieved evidence",
      rows: [
        ["Source", passage.source],
        ["Applicability", passage.path],
        ["Text", passage.text],
        ["Provenance", "team-authored, synthetic"],
      ],
    };
  const column = columns.find((c) => c.source === id);
  if (column)
    return {
      title: column.source,
      tag: "Column mapping",
      rows: [
        ["Maps to", column.target],
        ["Validation", column.rule],
        ["Sample", column.sample],
        ["Origin", "heuristic proposal"],
      ],
    };
  return { title: id, tag: "Reference", rows: [["Status", "not found in mock data"]] };
}

export function Inspector({ selection, decisions }: { selection: Selection; decisions: Record<string, Decision> }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center border-b border-line px-4">
        <p className="text-[15px] font-semibold text-fg">Inspector</p>
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto p-4">
        <AnimatePresence mode="wait">
          {selection ? (
            <motion.div
              key={selection.id}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.3, ease: EASE }}
            >
              {(() => {
                const info = resolve(selection, decisions);
                return (
                  <>
                    <Badge t="accent">{info.tag}</Badge>
                    <h3 className="mt-3 font-mono text-[14px] text-fg">{info.title}</h3>
                    <dl className="mt-3">
                      {info.rows.map(([k, v]) => (
                        <Row key={k} k={k} v={v} mono={k !== "Text"} />
                      ))}
                    </dl>
                  </>
                );
              })()}
            </motion.div>
          ) : (
            <motion.p key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-[14px] text-fg-3">
              Select an ID to see its source.
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
