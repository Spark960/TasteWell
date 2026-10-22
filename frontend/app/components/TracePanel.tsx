"use client";

import { useEffect, useRef, useMemo, useState } from "react";
import type { TraceEvent } from "@/lib/api";
import { StatusChip } from "./StatusChip";

function fmtTs(ts: string): string {
  // ts = "2026-10-21T12:34:56Z"-ish; show only the clock
  const m = ts.match(/T(\d{2}:\d{2}:\d{2})/);
  return m ? m[1] : ts;
}

function EventRow({
  ev,
  pane,
}: {
  ev: TraceEvent;
  pane: "grounded" | "generic";
}) {
  const desc = useMemo(() => {
    switch (ev.type) {
      case "run_started":
        return `brief: ${ev.brief ?? ""} · region: ${ev.region || "—"} · audience: ${ev.audience || "—"}`;
      case "status":
        return String(ev.message ?? "");
      case "llm":
        return `step ${ev.step}${(ev.tool_calls as string[] | undefined)?.length ? ` → ${(ev.tool_calls as string[]).join(", ")}` : " → final"}`;
      case "llm_started":
        return `step ${ev.step} → waiting on model response…`;
      case "tool_call": {
        const args = JSON.stringify(ev.args ?? {});
        return `${ev.tool} ${args.length > 80 ? args.slice(0, 80) + "…" : args}`;
      }
      case "tool_result":
        return `${ev.tool} → ${ev.summary ?? ""}${ev.error_code ? ` [${ev.error_code}]` : ""}`;
      case "user_choice":
        return `picked ${ev.pick}`;
      case "final":
        return "concept brief ready";
      case "run_done":
        return `exit=${ev.exit_status} (${ev.run_status})${ev.error ? ` · ${ev.error}` : ""}`;
      default:
        return "";
    }
  }, [ev]);

  const paneDot =
    pane === "grounded" ? "bg-teal-400" : "bg-zinc-500";
  const paneTag = pane === "grounded" ? "Q+" : "noQ";

  return (
    <li className="flex items-start gap-2 px-3 py-1 font-mono text-[11px] leading-relaxed hover:bg-zinc-900/60">
      <span className="shrink-0 text-zinc-600">{fmtTs(ev.ts)}</span>
      <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${paneDot}`} />
      <span className="shrink-0 text-zinc-600" title={pane === "grounded" ? "grounded run" : "ungrounded run"}>
        {paneTag}
      </span>
      <span className="w-20 shrink-0 text-zinc-400">{ev.type}</span>
      <span className="min-w-0 flex-1 truncate text-zinc-500" title={desc}>
        {desc}
      </span>
      {ev.type === "tool_result" && typeof ev.status === "string" && (
        <StatusChip status={ev.status} />
      )}
    </li>
  );
}

export function TracePanel({
  groundedEvents,
  genericEvents,
}: {
  groundedEvents: TraceEvent[];
  genericEvents: TraceEvent[];
}) {
  const hasEvents =
    groundedEvents.length > 0 || genericEvents.length > 0;
  // Opens itself as soon as trace events exist; user click takes over.
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const open = userOpen ?? hasEvents;
  const [filter, setFilter] = useState<"all" | "grounded" | "generic" | "tools">(
    "all",
  );

  const rows = useMemo(() => {
    const merged: Array<{ ev: TraceEvent; pane: "grounded" | "generic" }> = [
      ...groundedEvents.map((ev) => ({ ev, pane: "grounded" as const })),
      ...genericEvents.map((ev) => ({ ev, pane: "generic" as const })),
    ].sort((a, b) => a.ev.ts.localeCompare(b.ev.ts));
    if (filter === "grounded") return merged.filter((r) => r.pane === "grounded");
    if (filter === "generic") return merged.filter((r) => r.pane === "generic");
    if (filter === "tools")
      return merged.filter(
        (r) => r.ev.type === "tool_call" || r.ev.type === "tool_result",
      );
    return merged;
  }, [groundedEvents, genericEvents, filter]);

  return (
    <section
      className="rounded-xl border border-zinc-800 bg-zinc-900/40"
      aria-label="Live trace panel"
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setUserOpen(!open)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs font-medium text-zinc-400 hover:text-zinc-200"
      >
        <span className={`transition-transform ${open ? "rotate-90" : ""}`}>
          ▸
        </span>
        Live trace
        <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
          {rows.length} events
        </span>
      </button>
      {open && (
        <div className="border-t border-zinc-800">
          <div className="flex items-center gap-1.5 px-3 py-2">
            {(["all", "grounded", "generic", "tools"] as const).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`rounded-full border px-2 py-0.5 text-[10px] transition ${
                  filter === f
                    ? "border-teal-500/60 bg-teal-500/10 text-teal-200"
                    : "border-zinc-700 text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {f}
              </button>
            ))}
            <span className="ml-auto text-[10px] text-zinc-500">
              Q+ grounded · noQ ungrounded
            </span>
          </div>
          <ul className="max-h-64 overflow-y-auto pb-2">
            {rows.map((r, i) => (
              <EventRow key={i} ev={r.ev} pane={r.pane} />
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function LiveTrace({
  events,
  pane,
  maxRows = 14,
}: {
  events: TraceEvent[];
  pane: "grounded" | "generic";
  maxRows?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = containerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  const rows = events.slice(-maxRows);
  return (
    <div
      ref={containerRef}
      className="max-h-44 overflow-y-auto rounded-md border border-zinc-800 bg-zinc-900/70"
      aria-label="Live trace"
    >
      <ul>
        {rows.map((ev, i) => (
          <EventRow key={events.length - rows.length + i} ev={ev} pane={pane} />
        ))}
      </ul>
    </div>
  );
}
