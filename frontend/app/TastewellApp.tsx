"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import {
  fetchRunSummary,
  startRun,
  streamRun,
  type Brief,
  type Candidate,
  type RunPayload,
  type TraceEvent,
} from "@/lib/api";
import { BriefForm } from "./components/BriefForm";
import { ResultPane } from "./components/ResultPane";
import { TracePanel } from "./components/TracePanel";

type Phase =
  | "idle"
  | "starting"
  | "running"
  | "needs_input"
  | "done"
  | "error";

type Pane = {
  runId: string | null;
  events: TraceEvent[];
  brief: Brief | null;
  needsInput: { reason: string; candidates: Candidate[] } | null;
  phase: Phase;
  error: string | null;
  startedAt: number | null;
};

function emptyPane(): Pane {
  return {
    runId: null,
    events: [],
    brief: null,
    needsInput: null,
    phase: "idle",
    error: null,
    startedAt: null,
  };
}

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

const DISCLAIMER =
  "Aggregate cultural affinity data. Describes group tendencies, not individual behavior.";

type BasePayload = { brief: string; region: string; audience: string; pick?: string };

export default function TastewellApp() {
  const [grounded, setGrounded] = useState<Pane>(emptyPane);
  const [generic, setGeneric] = useState<Pane>(emptyPane);
  const [running, setRunning] = useState(false);
  const lastPayload = useRef<BasePayload | null>(null);
  const controllers = useRef<Set<AbortController>>(new Set());

  const drive = useCallback(
    async (
      mode: "grounded" | "generic",
      base: BasePayload,
      set: React.Dispatch<React.SetStateAction<Pane>>,
      signal: AbortSignal,
    ) => {
      set({ ...emptyPane(), phase: "starting" });
      let runId: string;
      try {
        runId = await startRun({ ...base, mode } as RunPayload);
      } catch (e) {
        if (signal.aborted) return;
        set({ ...emptyPane(), phase: "error", error: errText(e) });
        return;
      }
      set((p) => ({ ...p, phase: "running", runId, startedAt: Date.now() }));
      try {
        let brief: Brief | null = null;
        let exit = "";
        let fatal: string | null = null;
        const evs: TraceEvent[] = [];
        for await (const ev of streamRun(runId, signal)) {
          evs.push(ev);
          if (ev.type === "final") brief = ev.brief as Brief;
          if (ev.type === "run_done") {
            exit = String(ev.exit_status ?? "");
            const runErr = ev.error;
            fatal =
              typeof runErr === "string" && runErr ? runErr : null;
          }
          set((p) => ({ ...p, events: [...evs] }));
        }
        if (signal.aborted) return;
        if (exit === "needs_input") {
          const summary = await fetchRunSummary(runId, signal);
          if (signal.aborted) return;
          set({
            ...emptyPane(),
            runId,
            brief,
            events: evs,
            phase: "needs_input",
            needsInput: summary.needs_input,
          });
        } else if (exit === "ok") {
          set({ ...emptyPane(), runId, brief, events: evs, phase: "done" });
        } else {
          set({
            ...emptyPane(),
            runId,
            events: evs,
            phase: "error",
            error: fatal ?? `run ended with exit=${exit || "unknown"}`,
          });
        }
      } catch (e) {
        if (signal.aborted) return;
        set({ ...emptyPane(), runId, phase: "error", error: errText(e) });
      }
    },
    [],
  );

  const runBoth = useCallback(
    async (base: BasePayload) => {
      if (running) return;
      setRunning(true);
      lastPayload.current = base;
      for (const ctl of controllers.current) ctl.abort();
      controllers.current.clear();
      const gCtl = new AbortController();
      const uCtl = new AbortController();
      controllers.current.add(gCtl);
      controllers.current.add(uCtl);
      try {
        await Promise.allSettled([
          drive("grounded", base, setGrounded, gCtl.signal),
          drive("generic", base, setGeneric, uCtl.signal),
        ]);
      } finally {
        controllers.current.delete(gCtl);
        controllers.current.delete(uCtl);
        setRunning(false);
      }
    },
    [drive, running],
  );

  const cancel = useCallback(() => {
    for (const ctl of controllers.current) ctl.abort();
  }, []);

  const reDrive = useCallback(
    (mode: "grounded" | "generic", pick: Candidate) => {
      if (!lastPayload.current) return;
      const base = { ...lastPayload.current, pick: pick.id };
      lastPayload.current = base;
      const ctl = new AbortController();
      controllers.current.add(ctl);
      const set = mode === "grounded" ? setGrounded : setGeneric;
      drive(mode, base, set, ctl.signal)
        .catch(() => undefined)
        .finally(() => controllers.current.delete(ctl));
    },
    [drive],
  );

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-6">
      <header className="mb-6">
        <Link href="/decision" className="float-right rounded-md border border-amber-400 px-3 py-2 text-sm text-amber-300">Try programming decision</Link>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-50">
          Tastewell
        </h1>
        <p className="text-sm text-zinc-400">
          Tells a venue what the people around it actually like.
        </p>
      </header>

      <div className="grid min-h-0 flex-1 gap-5 lg:grid-cols-[300px_1fr]">
        <aside className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <BriefForm running={running} onRun={runBoth} onCancel={cancel} />
        </aside>

        <main className="grid min-h-0 gap-5 lg:grid-rows-[minmax(0,1.5fr)_minmax(0,0.8fr)_minmax(0,0.8fr)]">
          <ResultPane
            mode="grounded"
            phase={grounded.phase}
            brief={grounded.brief}
            error={grounded.error}
            needsInput={grounded.needsInput}
            startedAt={grounded.startedAt}
            events={grounded.events}
            onPick={(c) => reDrive("grounded", c)}
          />
          <TracePanel
            groundedEvents={grounded.events}
            genericEvents={generic.events}
          />
          <ResultPane
            mode="generic"
            phase={generic.phase}
            brief={generic.brief}
            error={generic.error}
            needsInput={generic.needsInput}
            startedAt={generic.startedAt}
            events={generic.events}
            onPick={(c) => reDrive("generic", c)}
          />
        </main>
      </div>

      <footer className="mt-4 text-center text-[11px] text-zinc-500">
        {DISCLAIMER}
      </footer>
    </div>
  );
}
