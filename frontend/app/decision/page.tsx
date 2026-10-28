"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";
import { parseVenueCsv } from "./venueCsv";
import "./decision.css";

type Evidence = {
  id: string; operation: string; status: string; source_id: string | null;
  name: string | null; affinity: number | null; query: Record<string, unknown>;
  correlation_id: string | null; retrieved_at: string; summary: string | null;
};
type Option = {
  id: string; title: string; description: string; format: string;
  evidence_ids: string[]; unknowns: string[]; constraint_notes: string[];
  artist_rank: number | null;
  venue_ranks: Record<string, number | null>;
};
type Venue = {
  id: string; name: string; region: string;
  live_music_allowed: boolean; budget_limit: number | null;
};
type Scenario = {
  id: string; venue_id: string; status: "ready" | "no_evidence";
  original_query: Record<string, unknown>; changed_query: Record<string, unknown>;
  artist_ids: string[]; artist_names: Record<string, string>;
  baseline_ranks: Record<string, number | null>;
  scenario_ranks: Record<string, number | null>;
  evidence_ids: string[]; note: string; created_at: string;
};
type Decision = {
  id: string; status: "ready" | "needs_input" | "no_evidence" | "blocked";
  source_mode?: "live" | "replay"; replay_of?: string | null;
  candidates: { id: string; name?: string; type?: string }[];
  options: Option[]; evidence: Evidence[]; notes: string[];
  selected_option_id: string | null; selected_at: string | null;
  pilot_plan: PilotPlan | null;
  outcome: PilotOutcome | null;
  venues: Venue[];
  resolution_kind: "tag" | "artist" | null;
  resolution_key: string | null;
  request?: { audience: string };
  scenarios?: Scenario[];
};
type PilotPlan = {
  venue_id: string;
  owner: string; target_date: string; success_measure: string;
  baseline: string; cost_assumption: string; next_action: string;
};
type PilotOutcome = {
  metric: string; baseline_value: number; actual_value: number;
  unit: string; period: string; source: string; notes: string;
};
type SavedDecision = {
  id: string; venue_name: string; concept: string; region: string;
  status: string; source_mode?: "live" | "replay"; selected_option_id: string | null;
  has_outcome: boolean; updated_at: string;
};
type Form = {
  venue_name: string; concept: string; region: string; audience: string;
  objective: string; budget_limit: string; live_music_allowed: boolean;
};
const initial: Form = {
  venue_name: "", concept: "", region: "", audience: "",
  objective: "Choose a weekly programming pilot", budget_limit: "",
  live_music_allowed: true,
};

export default function DecisionPage() {
  const [form, setForm] = useState<Form>(initial);
  const [extraVenues, setExtraVenues] = useState<{
    name: string; region: string; live_music_allowed: boolean; budget_limit: string;
  }[]>([]);
  const [artistShortlist, setArtistShortlist] = useState("");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStage, setJobStage] = useState("");
  const activeJob = useRef<string | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<SavedDecision[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [pendingOption, setPendingOption] = useState<string | null>(null);
  const [scenarioInput, setScenarioInput] = useState<{
    venue_id: string; audience: string | null; region: string | null;
  }>({ venue_id: "", audience: null, region: null });
  const [pilot, setPilot] = useState<PilotPlan>({
    venue_id: "", owner: "", target_date: "", success_measure: "", baseline: "",
    cost_assumption: "", next_action: "Confirm artist availability and fee",
  });
  const [quotedCost, setQuotedCost] = useState("");
  const [outcome, setOutcome] = useState({
    metric: "Attendance", baseline_value: "", actual_value: "",
    unit: "people", period: "One pilot event", source: "", notes: "",
  });

  async function importVenues(file?: File) {
    if (!file) return;
    setError("");
    try {
      if (file.size > 100_000) throw new Error("Venue CSV must be under 100 KB");
      const venues = parseVenueCsv(await file.text());
      const [first, ...rest] = venues;
      setForm((current) => ({ ...current, venue_name: first.name, region: first.region,
        live_music_allowed: first.live_music_allowed, budget_limit: first.budget_limit }));
      setExtraVenues(rest);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function loadHistory() {
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions`);
      if (!response.ok) throw new Error(`Could not load decisions (${response.status})`);
      setHistory(await response.json() as SavedDecision[]);
      setHistoryOpen(true);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function openDecision(id: string) {
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${id}`);
      if (!response.ok) throw new Error(`Could not open decision (${response.status})`);
      setDecision(await response.json() as Decision);
      setHistoryOpen(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function create(selectedTagId?: string) {
    setBusy(true); setError(""); setJobStage("Starting decision…");
    let startedJobId: string | null = null;
    try {
      const resolving = Boolean(selectedTagId && decision);
      const response = await fetch(resolving
        ? `${API_BASE}/api/decisions/${decision?.id}/resolve-jobs`
        : `${API_BASE}/api/decision-jobs`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resolving ? { candidate_id: selectedTagId } : {
          ...form,
          artist_shortlist: artistShortlist.split("\n").map((name) => name.trim()).filter(Boolean),
          budget_limit: form.budget_limit === "" ? null : Number(form.budget_limit),
          venues: [
            { name: form.venue_name, region: form.region,
              live_music_allowed: form.live_music_allowed,
              budget_limit: form.budget_limit === "" ? null : Number(form.budget_limit) },
            ...extraVenues.map((venue) => ({ ...venue,
              budget_limit: venue.budget_limit === "" ? null : Number(venue.budget_limit) })),
          ],
        }),
      });
      if (!response.ok) throw new Error(`Decision request failed (${response.status}): ${await response.text()}`);
      const started = await response.json() as { job_id: string };
      startedJobId = started.job_id;
      activeJob.current = started.job_id;
      setJobId(started.job_id);
      for (;;) {
        await new Promise((resolve) => setTimeout(resolve, 600));
        if (activeJob.current !== started.job_id) return;
        const poll = await fetch(`${API_BASE}/api/decision-jobs/${started.job_id}`);
        if (!poll.ok) throw new Error(`Could not check decision progress (${poll.status})`);
        const state = await poll.json() as {
          status: string; stage: string; elapsed_seconds: number;
          decision: Decision | null; error: string | null;
        };
        if (activeJob.current !== started.job_id) return;
        setJobStage(`${state.stage} · ${state.elapsed_seconds}s`);
        if (state.status === "done" && state.decision) {
          setDecision(state.decision);
          break;
        }
        if (state.status === "cancelled") break;
        if (state.status === "error") throw new Error(state.error || "Decision failed");
      }
    } catch (cause) {
      if (!startedJobId || activeJob.current === startedJobId)
        setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      if (!startedJobId || activeJob.current === startedJobId) {
        activeJob.current = null;
        setJobId(null);
        setBusy(false);
      }
    }
  }

  async function cancelCreate() {
    const id = activeJob.current;
    if (!id) return;
    setJobStage("Requesting cancellation…");
    try {
      const response = await fetch(`${API_BASE}/api/decision-jobs/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error(`Cancellation failed (${response.status})`);
      const state = await response.json() as { status: string; decision: Decision | null };
      activeJob.current = null;
      setJobId(null);
      if (state.status === "done" && state.decision) setDecision(state.decision);
      setJobStage(state.status === "done" ? "Complete" : "Cancellation requested");
      setBusy(false);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  }

  async function select(optionId: string) {
    if (!decision) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/select/${optionId}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...pilot,
          quoted_total_cost: quotedCost === "" ? null : Number(quotedCost),
          venue_id: pilot.venue_id || (decision.venues.length === 1 ? decision.venues[0].id : "") }),
      });
      if (!response.ok) throw new Error(`Selection failed (${response.status}): ${await response.text()}`);
      setDecision(await response.json() as Decision);
      setPendingOption(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setBusy(false); }
  }

  async function recordOutcome() {
    if (!decision) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/outcome`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...outcome,
          baseline_value: Number(outcome.baseline_value),
          actual_value: Number(outcome.actual_value),
        }),
      });
      if (!response.ok) throw new Error(`Outcome could not be recorded (${response.status}): ${await response.text()}`);
      setDecision(await response.json() as Decision);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  async function compareScenario() {
    if (!decision) return;
    const venue = decision.venues.find((item) => item.id === scenarioInput.venue_id)
      || decision.venues.find((item) => item.live_music_allowed);
    if (!venue) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/scenarios`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ venue_id: venue.id,
          audience: scenarioInput.audience ?? decision.request?.audience ?? form.audience,
          region: scenarioInput.region ?? venue.region }),
      });
      if (!response.ok) throw new Error(`Scenario failed (${response.status}): ${await response.text()}`);
      const result = await response.json() as { decision: Decision };
      setDecision(result.decision);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  async function replayDecision() {
    if (!decision) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/decisions/${decision.id}/replay`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(`Replay failed (${response.status})`);
      setDecision(await response.json() as Decision);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  }

  const fields: { key: keyof Form; label: string; placeholder: string }[] = [
    { key: "venue_name", label: "Venue", placeholder: "Your real venue name" },
    { key: "concept", label: "Venue concept", placeholder: "e.g. listening bar" },
    { key: "region", label: "Region", placeholder: "e.g. Williamsburg, Brooklyn" },
    { key: "audience", label: "Audience", placeholder: "e.g. young professionals" },
    { key: "objective", label: "Decision objective", placeholder: "What are you trying to choose?" },
    { key: "budget_limit", label: "Budget ceiling (optional)", placeholder: "Amount in your local currency" },
  ];
  const scenarioVenue = decision?.venues.find((venue) => venue.id === scenarioInput.venue_id)
    ?? decision?.venues.find((venue) => venue.live_music_allowed);

  return <div className="decision-shell">
    <header className="decision-topbar">
      <Link href="/" className="decision-brand" aria-label="Tastewell home"><span className="decision-brand-mark">t<span>.</span></span><span>tastewell</span></Link>
      <nav className="decision-nav" aria-label="Main navigation">
        <Link href="/" aria-current="page">Decisions</Link>
        <Link href="/compare">Compare Qloo</Link>
      </nav>
      <button onClick={() => void loadHistory()} className="decision-history-button">Saved decisions</button>
    </header>
    <div className="decision-layout">
    <aside className="decision-rail" aria-label="Decision guide">
      <div className="decision-rail-inner">
        <p className="decision-rail-label">Your decision trail</p>
        <h2>Better nights start with better questions.</h2>
        <p className="decision-rail-copy">Build a small, evidence-backed shortlist. Then choose a room, name the unknowns, and record what actually happened.</p>
        <ol className="decision-steps">
          <li className="is-active"><span>1</span><div><strong>Set the brief</strong><small>Rooms, audience &amp; limits</small></div></li>
          <li className={decision?.options.length ? "is-active" : ""}><span>2</span><div><strong>Explore options</strong><small>Ranks &amp; source evidence</small></div></li>
          <li className={decision?.selected_option_id ? "is-active" : ""}><span>3</span><div><strong>Plan the pilot</strong><small>Owner, timing &amp; measure</small></div></li>
          <li className={decision?.outcome ? "is-active" : ""}><span>4</span><div><strong>Record the outcome</strong><small>What your own data shows</small></div></li>
        </ol>
        <div className="decision-rail-note"><strong>What Qloo brings</strong><p>Aggregate cultural signals to compare a shortlist. Availability, costs, and results stay with your team.</p></div>
      </div>
    </aside>
    <main className="decision-main">
    <section className="decision-intro">
      <h1>Make the next night count.</h1>
      <p>Find an artist-led pilot that fits your audience and your venues. Keep the evidence and the operational questions together as you decide.</p>
      <div className="decision-scope"><span className="decision-scope-dot" />Currently exploring <strong>live music</strong> <span aria-hidden="true">·</span> Up to 10 venues</div>
    </section>
    {historyOpen && <section className="decision-history mb-5 rounded-xl border border-zinc-700 bg-zinc-900 p-4">
      <h2 className="font-semibold">Recent decisions</h2>
      {history.length === 0 && <p className="mt-2 text-sm text-zinc-400">No decisions saved yet.</p>}
      <div className="mt-3 grid gap-2">{history.map((item) =>
        <button key={item.id} onClick={() => void openDecision(item.id)}
          className="rounded-md border border-zinc-700 p-3 text-left text-sm hover:border-amber-400">
          {item.venue_name} · {item.concept} · {item.region}
          <span className="block text-xs text-zinc-500">{item.source_mode === "replay" ? "Replay · " : ""}{item.has_outcome ? "Outcome recorded" : item.selected_option_id ? "Pilot selected" : item.status} · {item.updated_at}</span>
        </button>)}</div></section>}
    <form id="decision-brief" onSubmit={(event) => { event.preventDefault(); void create(); }} className="decision-form rounded-xl border border-zinc-700 bg-zinc-900 p-5">
      <div className="decision-form-heading"><div><h2>Shape your pilot brief</h2><p>Start with the venue and the people you want to reach.</p></div><span>01 / Brief</span></div>
      <div className="grid gap-4 sm:grid-cols-2">{fields.map(({ key, label, placeholder }) =>
        <label key={key} className="text-sm text-zinc-300">{label}
          <input required={key !== "budget_limit"} type={key === "budget_limit" ? "number" : "text"}
            min={key === "budget_limit" ? 0 : undefined} placeholder={placeholder}
            value={String(form[key])} onChange={(event) => setForm({ ...form, [key]: event.target.value })}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2 text-zinc-100" />
        </label>)}</div>
      <label className="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" checked={form.live_music_allowed}
        onChange={(event) => setForm({ ...form, live_music_allowed: event.target.checked })} />Live music is permitted at this venue</label>
      <div className="decision-venues mt-5 border-t border-zinc-700 pt-4">
        <div className="flex items-center justify-between gap-3"><h2 className="font-medium">Additional venues</h2>
          <button type="button" disabled={extraVenues.length >= 9} onClick={() => setExtraVenues([...extraVenues,
            { name: "", region: "", live_music_allowed: true, budget_limit: "" }])}
            className="rounded-md border border-zinc-600 px-3 py-1 text-sm disabled:opacity-50">Add venue</button></div>
        <label className="mt-3 block text-xs text-zinc-400">Import venue CSV (replaces the venue fields above; 1–10 rows)
          <input type="file" accept=".csv,text/csv" onChange={(event) => { void importVenues(event.target.files?.[0]); event.target.value = ""; }}
            className="mt-1 block w-full text-sm" />
        </label>
        <p className="text-xs text-zinc-500">Columns: name,region,live_music_allowed,budget_limit. Use true/false; leave budget blank when unknown.</p>
        {extraVenues.map((venue, index) => <div key={index} className="mt-3 grid gap-3 rounded-lg border border-zinc-700 p-3 sm:grid-cols-2">
          <label className="text-sm">Venue name<input required value={venue.name}
            onChange={(event) => setExtraVenues(extraVenues.map((item, i) => i === index ? { ...item, name: event.target.value } : item))}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" /></label>
          <label className="text-sm">Region<input required value={venue.region}
            onChange={(event) => setExtraVenues(extraVenues.map((item, i) => i === index ? { ...item, region: event.target.value } : item))}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" /></label>
          <label className="text-sm">Budget ceiling (optional)<input type="number" min="0" value={venue.budget_limit}
            onChange={(event) => setExtraVenues(extraVenues.map((item, i) => i === index ? { ...item, budget_limit: event.target.value } : item))}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" /></label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={venue.live_music_allowed}
            onChange={(event) => setExtraVenues(extraVenues.map((item, i) => i === index ? { ...item, live_music_allowed: event.target.checked } : item))} />Live music permitted</label>
          <button type="button" onClick={() => setExtraVenues(extraVenues.filter((_, i) => i !== index))}
            className="text-left text-xs text-zinc-400 underline">Remove venue</button>
        </div>)}
      </div>
      <label className="decision-shortlist mt-5 block text-sm text-zinc-300">Your artist shortlist (optional; one name per line, up to five)
        <textarea rows={3} value={artistShortlist} onChange={(event) => setArtistShortlist(event.target.value)}
          placeholder={"Miles Davis\nAnother act you are considering"}
          className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2 text-zinc-100" />
      </label>
      <button disabled={busy} className="decision-primary mt-5 rounded-md bg-amber-400 px-4 py-2 font-semibold text-zinc-950 disabled:opacity-50">{busy ? "Checking Qloo…" : "Explore options"}</button>
      {jobId && <button type="button" onClick={() => void cancelCreate()}
        className="ml-3 rounded-md border border-zinc-600 px-4 py-2 text-sm">Cancel decision</button>}
      {jobStage && <p role="status" className="mt-2 text-xs text-zinc-400">{jobStage}</p>}
    </form>
    {error && <p role="alert" className="mt-5 rounded-md border border-red-700 p-3 text-red-300">{error}</p>}
    {decision && <section id="decision-options" className="decision-results mt-8" aria-live="polite">
      <h2 className="text-xl font-semibold">{decision.status === "ready" ? "Pilot options" : "Decision needs attention"}</h2>
      <p className="mt-1 text-xs text-zinc-500">Decision {decision.id} · {decision.source_mode === "replay"
        ? `Replay of ${decision.replay_of}; no new Qloo call` : "Current decision"} · Saved on this server.</p>
      <div className="mt-3 flex flex-wrap gap-3 text-xs">
        <button disabled={busy} onClick={() => void replayDecision()}
          className="rounded-md border border-zinc-600 px-3 py-2">Replay saved evidence</button>
        <a href={`${API_BASE}/api/decisions/${decision.id}/export`}
          className="rounded-md border border-zinc-600 px-3 py-2">Export decision JSON</a>
      </div>
      {decision.notes.map((note, i) => <p key={i} className="mt-2 text-sm text-zinc-300">{note}</p>)}
      {decision.status === "needs_input" && <div className="mt-4 rounded-lg border border-amber-700 p-4">
        <h3 className="font-medium">{decision.resolution_kind === "artist"
          ? `Choose the intended artist for ${decision.resolution_key}`
          : "Choose the intended concept tag"}</h3>
        <div className="mt-3 flex flex-wrap gap-2">{decision.candidates.map((candidate) =>
          <button key={candidate.id} disabled={busy} onClick={() => void create(candidate.id)}
            className="rounded-md border border-zinc-600 px-3 py-2 text-left text-sm hover:border-amber-400">
            {candidate.name || candidate.id}<span className="block text-xs text-zinc-500">{candidate.type}</span></button>)}</div>
      </div>}
      <div className="decision-options-grid mt-5 grid gap-4 md:grid-cols-3">{decision.options.map((option, index) =>
        <article key={option.id} className="decision-option rounded-xl border border-zinc-700 bg-zinc-900 p-4">
          <div className="decision-option-top"><span>Option {String(index + 1).padStart(2, "0")}</span><span>{option.evidence_ids.length} sources</span></div>
          <h3 className="font-semibold">{option.title}</h3><p className="mt-2 text-sm">{option.description}</p>
          {option.artist_rank && <p className="mt-2 text-xs text-amber-300">Artist #{option.artist_rank} within this Qloo shortlist</p>}
          {decision.venues.length > 1 && <div className="mt-3 border-t border-zinc-700 pt-3 text-xs">
            <p className="font-medium text-zinc-300">Venue comparison · rank within each separate call</p>
            {decision.venues.map((venue) => <p key={venue.id} className="mt-1 text-zinc-400">
              {venue.name}: {!venue.live_music_allowed ? "Excluded · no live music" : option.venue_ranks[venue.id] ? `artist #${option.venue_ranks[venue.id]}` : "rank unavailable"}
            </p>)}
          </div>}
          <p className="mt-4 text-xs uppercase tracking-wide text-zinc-500">What is unknown</p>
          <ul className="mt-1 list-inside list-disc text-sm text-zinc-300">{option.unknowns.map((item) => <li key={item}>{item}</li>)}</ul>
          <p className="mt-3 text-xs text-zinc-400">{option.constraint_notes.join(" ")}</p>
          <details className="mt-4 text-xs"><summary className="cursor-pointer text-amber-300">Inspect Qloo evidence</summary>
            {option.evidence_ids.map((id) => { const row = decision.evidence.find((e) => e.id === id);
              return row && <div key={id} className="mt-2 break-words border-t border-zinc-700 pt-2">
                <strong>{row.name || row.source_id}</strong> · {row.operation} · {row.status}
                <div>ID: {row.source_id}</div><div>Affinity: {row.affinity ?? "not provided"}</div>
                <div>Query: {JSON.stringify(row.query)}</div><div>Correlation: {row.correlation_id || "not provided"}</div>
                <div>Retrieved: {row.retrieved_at}</div></div>; })}</details>
          <button onClick={() => setPendingOption(option.id)} disabled={busy}
            className="mt-4 rounded-md border border-amber-400 px-3 py-2 text-sm text-amber-300 disabled:opacity-50">
            {decision.selected_option_id === option.id ? "Selected · edit plan" : "Plan this pilot"}</button>
        </article>)}</div>
      {decision.status === "ready" && decision.options.some((option) => option.artist_rank) &&
        <section className="decision-scenario mt-6 rounded-xl border border-zinc-700 bg-zinc-900 p-5">
          <h3 className="font-semibold">Scenario comparison</h3>
          <p className="mt-1 text-sm text-zinc-400">Keep the artist IDs fixed and change one audience or region. Each rank is within its own Qloo call.</p>
          <form onSubmit={(event) => { event.preventDefault(); void compareScenario(); }}
            className="mt-4 grid gap-3 sm:grid-cols-3">
            <label className="text-sm">Venue
              <select value={scenarioVenue?.id || ""}
                onChange={(event) => { const venue = decision.venues.find((item) => item.id === event.target.value);
                  setScenarioInput({ ...scenarioInput, venue_id: event.target.value, region: venue?.region ?? null }); }}
                className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2">
                {decision.venues.filter((venue) => venue.live_music_allowed).map((venue) =>
                  <option key={venue.id} value={venue.id}>{venue.name}</option>)}
              </select>
            </label>
            <label className="text-sm">Scenario audience
              <input required value={scenarioInput.audience ?? decision.request?.audience ?? form.audience}
                onChange={(event) => setScenarioInput({ ...scenarioInput, audience: event.target.value })}
                className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
            </label>
            <label className="text-sm">Scenario region
              <input required value={scenarioInput.region ?? scenarioVenue?.region ?? ""}
                onChange={(event) => setScenarioInput({ ...scenarioInput, region: event.target.value })}
                className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
            </label>
            <button disabled={busy} className="rounded-md bg-amber-400 px-4 py-2 font-semibold text-zinc-950 disabled:opacity-50">Compare scenario</button>
          </form>
          {(decision.scenarios || []).slice().reverse().map((scenario) =>
            <div key={scenario.id} className="mt-5 border-t border-zinc-700 pt-4 text-sm">
              <p className="font-medium">{decision.venues.find((venue) => venue.id === scenario.venue_id)?.name} · {scenario.status === "ready" ? "Ranked" : "Rank unavailable"}</p>
              <p className="mt-1 text-zinc-400">{scenario.note}</p>
              <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs">
                <thead><tr><th className="pb-2">Artist</th><th>Original rank</th><th>Scenario rank</th><th>Change</th></tr></thead>
                <tbody>{scenario.artist_ids.map((id) => { const before = scenario.baseline_ranks[id]; const after = scenario.scenario_ranks[id];
                  return <tr key={id} className="border-t border-zinc-700">
                    <td className="py-2">{scenario.artist_names[id] || id}</td>
                    <td>{before ?? "unavailable"}</td><td>{after ?? "unavailable"}</td>
                    <td>{before && after ? before === after ? "unchanged" : after < before ? `up ${before - after}` : `down ${after - before}` : "unknown"}</td>
                  </tr>; })}</tbody>
              </table></div>
              <details className="mt-3 text-xs"><summary className="cursor-pointer text-amber-300">Inspect scenario queries and evidence</summary>
                <p className="mt-2 break-words">Original: {JSON.stringify(scenario.original_query)}</p>
                <p className="mt-1 break-words">Changed: {JSON.stringify(scenario.changed_query)}</p>
                {scenario.evidence_ids.map((id) => { const row = decision.evidence.find((item) => item.id === id);
                  return row && <p key={id} className="mt-1 break-words">{row.name || row.source_id || "No entity"} · {row.status} · {row.source_id || "No ID"} · {row.correlation_id || "No correlation"}</p>; })}
              </details>
            </div>)}
        </section>}
      {pendingOption && <form onSubmit={(event) => { event.preventDefault(); void select(pendingOption); }}
        className="decision-plan mt-6 rounded-xl border border-amber-700 bg-zinc-900 p-5">
        <h3 className="text-lg font-semibold">Record the pilot</h3>
        <p className="mt-1 text-sm text-zinc-400">Use your own operational facts. Qloo does not provide booking, cost, or outcome data.</p>
        <label className="mt-4 block text-sm">Pilot venue
          <select required value={pilot.venue_id || (decision.venues.length === 1 ? decision.venues[0].id : "")}
            onChange={(event) => setPilot({ ...pilot, venue_id: event.target.value })}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2">
            <option value="">Choose a venue</option>
            {decision.venues.filter((venue) => venue.live_music_allowed).map((venue) =>
              <option key={venue.id} value={venue.id}>{venue.name} · {venue.region}</option>)}
          </select>
        </label>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">{([
          ["owner", "Owner"], ["target_date", "Target date or window"],
          ["success_measure", "Success measure"], ["baseline", "Baseline source or value"],
          ["cost_assumption", "Cost assumption"], ["next_action", "Next action"],
        ] as [keyof PilotPlan, string][]).map(([key, label]) =>
          <label key={key} className="text-sm">{label}
            <input required={key === "owner" || key === "target_date" || key === "success_measure" || key === "next_action"}
              value={pilot[key]} onChange={(event) => setPilot({ ...pilot, [key]: event.target.value })}
              className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
          </label>)}</div>
        <label className="mt-3 block text-sm">Known total pilot cost (optional; same currency as venue budget)
          <input type="number" min="0" step="1" value={quotedCost}
            onChange={(event) => setQuotedCost(event.target.value)}
            className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
        </label>
        <p className="mt-1 text-xs text-zinc-500">When supplied, this amount must not exceed the selected venue&apos;s budget ceiling. Unknown cost remains unverified.</p>
        <button disabled={busy} className="mt-4 rounded-md bg-amber-400 px-4 py-2 font-semibold text-zinc-950">Record selection</button>
      </form>}
      {decision.selected_option_id && <p className="mt-5 rounded-md border border-green-700 p-3 text-sm text-green-300">
        Selection recorded for {decision.venues.find((venue) => venue.id === decision.pilot_plan?.venue_id)?.name} on {decision.pilot_plan?.target_date}. Owner: {decision.pilot_plan?.owner}. Next: {decision.pilot_plan?.next_action}.</p>}
      {decision.selected_option_id && <div className="decision-outcome mt-5 rounded-xl border border-zinc-700 bg-zinc-900 p-5">
        <h3 className="font-semibold">Pilot outcome</h3>
        <p className="mt-1 text-sm text-zinc-400">Enter aggregated results from your own records. A difference from baseline does not establish that this program caused it.</p>
        {decision.outcome && <p className="mt-3 text-sm text-green-300">Recorded: {decision.outcome.metric} {decision.outcome.baseline_value} → {decision.outcome.actual_value} {decision.outcome.unit} ({decision.outcome.period}). Source: {decision.outcome.source}.</p>}
        <form onSubmit={(event) => { event.preventDefault(); void recordOutcome(); }} className="mt-4 grid gap-3 sm:grid-cols-2">
          {([
            ["metric", "Metric"], ["baseline_value", "Baseline value"],
            ["actual_value", "Actual value"], ["unit", "Unit"],
            ["period", "Measurement period"], ["source", "Operator data source"],
            ["notes", "Notes (optional)"],
          ] as [keyof typeof outcome, string][]).map(([key, label]) =>
            <label key={key} className="text-sm">{label}
              <input required={key !== "notes"} type={key.endsWith("_value") ? "number" : "text"}
                value={outcome[key]} onChange={(event) => setOutcome({ ...outcome, [key]: event.target.value })}
                className="mt-1 block w-full rounded-md border border-zinc-600 bg-zinc-950 p-2" />
            </label>)}
          <button disabled={busy} className="rounded-md bg-amber-400 px-4 py-2 font-semibold text-zinc-950 disabled:opacity-50">Record outcome</button>
        </form>
      </div>}
    </section>}
    <footer className="decision-footer mt-10 text-xs text-zinc-500">Qloo reports aggregate cultural affinity. It does not predict attendance, sales, or individual behavior.</footer>
    </main>
    </div>
  </div>;
}
