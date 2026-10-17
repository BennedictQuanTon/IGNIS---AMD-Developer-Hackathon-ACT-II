import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, request, type Health, type History, type Json, type Report, type Run } from "./api";

export function useWorkflow() {
  const [run, setRun] = useState<Run | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [history, setHistory] = useState<History>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [retryAt, setRetryAt] = useState(0);
  const [clock, setClock] = useState(Date.now());
  const lock = useRef(false);
  const current = useRef<Run | null>(null);
  const select = useCallback(async (value: Run) => {
    current.current = value;
    setRun(value);
    setRuns(previous => previous.map(item => item.run_id === value.run_id ? value : item));
    localStorage.setItem("ignis-active-run", value.run_id);
    setHistory([]); setReports([]);
    const extra = await Promise.allSettled([
      request<{ events: History }>(`/runs/${value.run_id}/history`),
      request<{ reports: Report[] }>(`/runs/${value.run_id}/reports`),
    ]);
    if (current.current?.run_id !== value.run_id || current.current.revision !== value.revision) return;
    if (extra[0].status === "fulfilled") setHistory(extra[0].value.events);
    if (extra[1].status === "fulfilled") setReports(extra[1].value.reports);
    if (extra.some(result => result.status === "rejected")) setError("Run saved, but history/report listing could not be refreshed. Refresh to retry these reads.");
  }, []);
  const perform = useCallback(async (label: string, action: () => Promise<void>) => {
    if (lock.current || Date.now() < retryAt) return;
    lock.current = true; setBusy(label); setError("");
    try { await action(); }
    catch (caught) {
      if (caught instanceof ApiError) {
        if (caught.status === 429) setRetryAt(Date.now() + caught.retryAfter * 1000);
        if (caught.payload.run) await select(caught.payload.run as Run);
        if (caught.status === 409 && current.current) {
          try { await select(await request<Run>(`/runs/${current.current.run_id}`)); } catch { /* Keep the last saved view. */ }
        }
        setError(caught.status === 409 ? "Another change was saved. Latest available state loaded; inspect it before retrying your decision." : caught.message);
      } else setError(caught instanceof Error ? caught.message : String(caught));
    } finally { lock.current = false; setBusy(""); }
  }, [retryAt, select]);
  const refresh = useCallback(() => perform("Refreshing saved state", async () => {
    const [runtime, listing] = await Promise.all([request<Health>("/health"), request<{ runs: Run[] }>("/runs")]);
    setHealth(runtime); setRuns(listing.runs);
    const saved = current.current?.run_id || localStorage.getItem("ignis-active-run");
    if (saved) {
      const available = listing.runs.find(value => value.run_id === saved);
      if (available) await select(available);
      else { current.current = null; setRun(null); setHistory([]); setReports([]); localStorage.removeItem("ignis-active-run"); }
    }
  }), [perform, select]);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { if (!retryAt) return; const timer = window.setInterval(() => setClock(Date.now()), 1000); return () => clearInterval(timer); }, [retryAt]);
  const mutate = (suffix: string, payload: Json = {}, label = "Saving") => perform(label, async () => {
    const value = current.current;
    if (!value) throw new Error("Create or choose a run first.");
    await select(await request<Run>(`/runs/${value.run_id}${suffix}`, { ...payload, expected_revision: value.revision }));
  });
  const create = async (payload: Json) => {
    const value = await request<Run>("/runs", payload);
    setRuns(previous => [value, ...previous]);
    await select(value);
    return value;
  };
  return { run, runs, health, history, reports, error, busy, cooldown: Math.max(0, Math.ceil((retryAt - clock) / 1000)),
    perform, select, refresh, mutate, create, setError };
}
