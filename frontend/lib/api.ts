// Typed client for the Tastewell FastAPI backend (P3 contract).
// No secrets ever live here — the browser talks to our backend only,
// never to Qloo or the LLM providers directly.

export type RunMode = "grounded" | "generic";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export type Candidate = {
  id: string;
  name?: string | null;
  type?: string | null;
  popularity?: number | null;
};

export type Evidence = {
  tool?: string;
  operation?: string;
  status?: string;
  summary?: string | null;
  ids?: string[];
  result_count?: number;
  error_code?: string | null;
  correlation_id?: string | null;
  ts?: string | null;
};

export type Brief = {
  audience_profile?: string;
  menu_tilt?: string[];
  music_programming?: string[];
  adjacent_brands?: string[];
  tag_themes?: string[];
  honest_absences?: string[];
  evidence?: Evidence[];
  disclaimers?: string[];
  raw?: string;
};

export type TraceEvent = {
  ts: string;
  type: string;
  [key: string]: unknown;
};

export type NeedsInput = {
  reason: string;
  candidates: Candidate[];
};

export type RunSummary = {
  run_id: string;
  status: string;
  exit_status: string | null;
  needs_input: NeedsInput | null;
  brief: Brief | null;
  events: number;
  error?: string;
};

export type RunPayload = {
  brief: string;
  region: string;
  audience: string;
  mode: RunMode;
  pick?: string;
};

export async function startRun(payload: RunPayload): Promise<string> {
  const res = await fetch(`${API_BASE}/api/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`run start failed (${res.status}): ${text}`);
  }
  const body = (await res.json()) as { run_id: string };
  return body.run_id;
}

export async function fetchRunSummary(
  runId: string,
  signal?: AbortSignal,
): Promise<RunSummary> {
  const res = await fetch(`${API_BASE}/api/agent/runs/${runId}`, { signal });
  if (!res.ok) {
    throw new Error(`run summary failed (${res.status})`);
  }
  return (await res.json()) as RunSummary;
}

/** Consume the SSE trace stream; yields parsed trace events until run_done. */
export async function* streamRun(
  runId: string,
  signal?: AbortSignal,
): AsyncGenerator<TraceEvent> {
  const res = await fetch(`${API_BASE}/api/agent/stream/${runId}`, { signal });
  if (!res.ok || !res.body) {
    throw new Error(`stream failed (${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        const ev = JSON.parse(line.slice(6)) as TraceEvent;
        yield ev;
        if (ev.type === "run_done") {
          // Run is over — stop reading immediately so the run can
          // transition to done/needs_input without waiting for the
          // server to close the SSE connection.
          await reader.cancel().catch(() => undefined);
          return;
        }
      } catch {
        // skip malformed frames; redactor output is trusted JSON otherwise
      }
    }
  }
}

export type QlooStatus = {
  ready: boolean;
  reason?: string;
  tools?: string[];
  capabilities_status?: string;
};

export async function fetchQlooStatus(): Promise<QlooStatus> {
  const res = await fetch(`${API_BASE}/api/qloo/status`);
  if (!res.ok) return { ready: false, reason: `status ${res.status}` };
  return (await res.json()) as QlooStatus;
}
