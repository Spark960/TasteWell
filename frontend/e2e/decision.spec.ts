import { expect, test } from "@playwright/test";

test("venue CSV import fills the portfolio and rejects malformed data", async ({ page }) => {
  await page.goto("/decision");
  const picker = page.getByLabel(/Import venue CSV/);
  await picker.setInputFiles({ name: "venues.csv", mimeType: "text/csv",
    buffer: Buffer.from('name,region,live_music_allowed,budget_limit\n"The Room, East",Brooklyn,true,1200\nAnnex,Queens,false,\n') });
  await expect(page.getByLabel("Venue", { exact: true })).toHaveValue("The Room, East");
  await expect(page.getByLabel("Venue name")).toHaveValue("Annex");
  await expect(page.getByLabel("Region").last()).toHaveValue("Queens");
  await expect(page.getByLabel("Live music permitted")).not.toBeChecked();
  await picker.setInputFiles({ name: "bad.csv", mimeType: "text/csv",
    buffer: Buffer.from("name,region,live_music_allowed,budget_limit\nBad,,perhaps,free\n") });
  await expect(page.getByText(/Venue CSV row 2 needs a valid name and region/)).toBeVisible();
  await expect(page.getByLabel("Venue", { exact: true })).toHaveValue("The Room, East");
});

const tag = "urn:tag:genre:music:jazz";
const evidence = [
  { id: "ev-tag", operation: "find_tags", status: "ok", source_id: tag, name: "Jazz", affinity: null, query: { query: "jazz" }, correlation_id: "c1", retrieved_at: "2026-10-27T00:00:00Z", summary: null },
  { id: "ev-artist", operation: "recommend", status: "ok", source_id: "artist-1", name: "First Act", affinity: 0.8, query: { target_type: "artist" }, correlation_id: "c2", retrieved_at: "2026-10-27T00:00:01Z", summary: null },
  { id: "ev-rank", operation: "rank", status: "ok", source_id: "artist-1", name: "First Act", affinity: 0.9, query: { options: ["artist-1"] }, correlation_id: "c3", retrieved_at: "2026-10-27T00:00:02Z", summary: null },
];
const option = {
  id: "opt-1", title: "Early live set", description: "Pilot an early set with First Act at The Room.",
  format: "early_set", evidence_ids: ["ev-tag", "ev-artist", "ev-rank"],
  unknowns: ["Artist availability and fee"], constraint_notes: ["Live music permitted."],
  artist_rank: 1,
};

test("operator resolves evidence, plans a pilot, records outcome, and reopens it", async ({ page }) => {
  let saved = {
    id: "dec-1", status: "needs_input", candidates: [{ id: tag, name: "Jazz", type: "genre:music" }],
    source_mode: "live" as "live" | "replay", replay_of: null as string | null,
    options: [] as typeof option[], evidence, notes: ["Choose the Qloo tag."],
    selected_option_id: null as string | null, selected_at: null as string | null,
    pilot_plan: null as Record<string, unknown> | null,
    outcome: null as Record<string, unknown> | null,
    venues: [{ id: "v1", name: "The Room", region: "Brooklyn", live_music_allowed: true, budget_limit: null }],
    resolution_kind: "tag" as "tag" | "artist" | null,
    resolution_key: null as string | null,
  };
  await page.route("**/api/decisions", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: [{ id: saved.id, venue_name: "The Room", concept: "jazz", region: "Brooklyn", status: saved.status, selected_option_id: saved.selected_option_id, has_outcome: Boolean(saved.outcome), updated_at: "2026-10-27" }] });
      return;
    }
    await route.fulfill({ json: saved });
  });
  await page.route("**/api/decision-jobs", async (route) => {
    await route.fulfill({ status: 202, json: { job_id: "job-1" } });
  });
  await page.route("**/api/decision-jobs/*", async (route) => {
    await route.fulfill({ json: { status: "done", stage: "complete",
      elapsed_seconds: 1, decision: saved, error: null } });
  });
  await page.route("**/api/decisions/**", async (route) => {
    const url = route.request().url();
    if (url.endsWith("/resolve-jobs")) {
      const body = route.request().postDataJSON() as { candidate_id: string };
      expect(body.candidate_id).toBe(tag);
      saved = { ...saved, status: "ready", candidates: [], options: [option], notes: ["Artist ranks compare one shortlist."], resolution_kind: null };
      await route.fulfill({ status: 202, json: { job_id: "job-2" } });
      return;
    } else if (url.endsWith("/replay")) {
      saved = { ...saved, id: "dec-replay", source_mode: "replay", replay_of: "dec-1",
        selected_option_id: null, selected_at: null, pilot_plan: null, outcome: null };
      await route.fulfill({ status: 201, json: saved });
      return;
    } else if (url.endsWith("/outcome")) {
      saved = { ...saved, outcome: route.request().postDataJSON() as Record<string, unknown> };
    } else if (url.includes("/select/")) {
      const plan = route.request().postDataJSON() as Record<string, unknown>;
      expect(plan.quoted_total_cost).toBe(75);
      saved = { ...saved, selected_option_id: "opt-1", selected_at: "2026-10-27", pilot_plan: plan };
    }
    await route.fulfill({ json: saved });
  });

  await page.goto("/decision");
  await page.getByLabel("Venue", { exact: true }).fill("The Room");
  await page.getByLabel("Venue concept").fill("jazz");
  await page.getByLabel("Region").fill("Brooklyn");
  await page.getByLabel("Audience").fill("millennials");
  await page.getByRole("button", { name: "Explore options" }).click();
  await expect(page.getByText("Choose the intended concept tag")).toBeVisible();
  await page.getByRole("button", { name: /Jazz Music genre/ }).click();
  await expect(page.getByText("Pilot an early set with First Act at The Room.")).toBeVisible();
  await page.getByText("Inspect Qloo evidence").click();
  await expect(page.getByText("ID: artist-1").first()).toBeVisible();
  await page.getByRole("button", { name: "Plan this pilot" }).click();
  await page.getByLabel("Owner").fill("Manager");
  await page.getByLabel("Target date or window").fill("Next Wednesday");
  await page.getByLabel("Success measure").fill("Attendance");
  await page.getByLabel(/Known total pilot cost/).fill("75");
  await page.getByRole("button", { name: "Record selection" }).click();
  await expect(page.getByText(/Selection recorded for The Room on Next Wednesday/)).toBeVisible();
  await page.getByLabel("Baseline value").fill("24");
  await page.getByLabel("Actual value").fill("31");
  await page.getByLabel("Operator data source").fill("Headcount sheet");
  await page.getByRole("button", { name: "Record outcome" }).click();
  await expect(page.getByText(/Attendance 24 → 31 people/)).toBeVisible();
  await page.getByRole("button", { name: "Saved decisions" }).click();
  await page.getByRole("button", { name: /The Room · jazz · Brooklyn/ }).click();
  await expect(page.getByText(/Attendance 24 → 31 people/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Export decision JSON" })).toHaveAttribute(
    "href", /\/api\/decisions\/dec-1\/export$/);
  await page.getByRole("button", { name: "Replay saved evidence" }).click();
  await expect(page.getByText(/Replay of dec-1; no new Qloo call/)).toBeVisible();
  await expect(page.getByText("Pilot an early set with First Act at The Room.")).toBeVisible();
});

test("operator shortlist compares eligible venues and resolves an artist", async ({ page }) => {
  const choices = [
    { id: "artist-a", name: "First Act", type: "artist" },
    { id: "artist-b", name: "First Act", type: "artist" },
  ];
  let saved = {
    id: "dec-portfolio", status: "needs_input", candidates: choices,
    resolution_kind: "artist" as "artist" | null, resolution_key: "First Act" as string | null,
    notes: ["Choose the intended Qloo artist."], evidence: [],
    options: [] as (typeof option & { venue_ranks: Record<string, number | null> })[],
    venues: [
      { id: "v1", name: "First Room", region: "Brooklyn", live_music_allowed: true, budget_limit: 500 },
      { id: "v2", name: "Second Room", region: "Queens", live_music_allowed: true, budget_limit: null },
      { id: "v3", name: "Quiet Room", region: "Harlem", live_music_allowed: false, budget_limit: null },
    ],
    selected_option_id: null as string | null, selected_at: null as string | null,
    pilot_plan: null as Record<string, unknown> | null, outcome: null,
    scenarios: [] as Record<string, unknown>[],
  };
  await page.route("**/api/decision-jobs", async (route) => {
    const body = route.request().postDataJSON() as {
      artist_shortlist: string[]; venues: { name: string; live_music_allowed: boolean }[];
    };
    expect(body.artist_shortlist).toEqual(["First Act", "Second Act"]);
    expect(body.venues.map((venue) => venue.name)).toEqual(["First Room", "Second Room", "Quiet Room"]);
    expect(body.venues[2].live_music_allowed).toBe(false);
    await route.fulfill({ status: 202, json: { job_id: "job-portfolio" } });
  });
  await page.route("**/api/decision-jobs/*", async (route) => {
    await route.fulfill({ json: { status: "done", stage: "complete",
      elapsed_seconds: 1, decision: saved, error: null } });
  });
  await page.route("**/api/decisions/**", async (route) => {
    if (route.request().url().endsWith("/resolve-jobs")) {
      expect(route.request().postDataJSON()).toEqual({ candidate_id: "artist-b" });
      saved = {
        ...saved, status: "ready", candidates: [], resolution_kind: null, resolution_key: null,
        notes: ["Ranks are within each venue's separate call."],
        options: [{ ...option, venue_ranks: { v1: 2, v2: 1, v3: null } }],
      };
      await route.fulfill({ status: 202, json: { job_id: "job-resolved" } });
      return;
    } else if (route.request().url().endsWith("/scenarios")) {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      expect(body).toEqual({ venue_id: "v1", audience: "young professionals", region: "Brooklyn" });
      saved = { ...saved, scenarios: [{
        id: "scenario-1", venue_id: "v1", status: "ready", created_at: "2026-10-27",
        original_query: { options: ["artist-a", "artist-b"], demographic: "millennials" },
        changed_query: { options: ["artist-a", "artist-b"], demographic: "young professionals" },
        artist_ids: ["artist-a", "artist-b"], artist_names: { "artist-a": "First Act", "artist-b": "Second Act" },
        baseline_ranks: { "artist-a": 1, "artist-b": 2 }, scenario_ranks: { "artist-a": 2, "artist-b": 1 },
        evidence_ids: [], note: "Rank positions compare the same artist IDs within each call.",
      }] };
      await route.fulfill({ json: { decision: saved, scenario: saved.scenarios[0] } });
      return;
    } else if (route.request().url().includes("/select/")) {
      const plan = route.request().postDataJSON() as Record<string, unknown>;
      saved = { ...saved, selected_option_id: "opt-1", selected_at: "2026-10-27",
        pilot_plan: plan };
      expect(plan.venue_id).toBe("v2");
    }
    await route.fulfill({ json: saved });
  });

  await page.goto("/decision");
  await page.getByLabel("Venue", { exact: true }).fill("First Room");
  await page.getByLabel("Venue concept").fill("jazz");
  await page.getByLabel("Region", { exact: true }).fill("Brooklyn");
  await page.getByLabel("Audience").fill("millennials");
  await page.getByLabel("Budget ceiling (optional)").first().fill("500");
  await page.getByRole("button", { name: "Add venue" }).click();
  await page.getByLabel("Venue name").last().fill("Second Room");
  await page.getByLabel("Region").last().fill("Queens");
  await page.getByRole("button", { name: "Add venue" }).click();
  await page.getByLabel("Venue name").last().fill("Quiet Room");
  await page.getByLabel("Region").last().fill("Harlem");
  await page.getByLabel("Live music permitted").last().uncheck();
  await page.getByLabel("Your artist shortlist").fill("First Act\nSecond Act");
  await page.getByRole("button", { name: "Explore options" }).click();
  await expect(page.getByText("Choose the intended artist for First Act")).toBeVisible();
  await page.getByRole("button", { name: /First Act Artist record/ }).last().click();
  await expect(page.getByText("Venue comparison · rank within each separate call")).toBeVisible();
  await expect(page.getByText("First Room: artist #2")).toBeVisible();
  await expect(page.getByText("Second Room: artist #1")).toBeVisible();
  await expect(page.getByText("Quiet Room: Excluded · no live music")).toBeVisible();
  await page.getByLabel("Scenario audience").fill("young professionals");
  await page.getByRole("button", { name: "Compare scenario" }).click();
  await expect(page.getByText("up 1")).toBeVisible();
  await page.getByText("Inspect scenario queries and evidence").click();
  await expect(page.getByText(/Changed:.*young professionals/)).toBeVisible();
  await page.getByRole("button", { name: "Plan this pilot" }).click();
  await expect(page.getByRole("option", { name: /Quiet Room/ })).toHaveCount(0);
  await page.getByLabel("Pilot venue").selectOption("v2");
  await page.getByLabel("Owner").fill("Manager");
  await page.getByLabel("Target date or window").fill("Next Wednesday");
  await page.getByLabel("Success measure").fill("Attendance");
  await page.getByRole("button", { name: "Record selection" }).click();
  await expect(page.getByText(/Selection recorded for Second Room/)).toBeVisible();
});

test("operator can cancel an in-flight decision job", async ({ page }) => {
  let cancelled = false;
  await page.route("**/api/decision-jobs", async (route) => {
    await route.fulfill({ status: 202, json: { job_id: "job-slow" } });
  });
  await page.route("**/api/decision-jobs/*", async (route) => {
    if (route.request().method() === "DELETE") {
      cancelled = true;
      await route.fulfill({ json: { job_id: "job-slow", status: "cancelled" } });
      return;
    }
    await route.fulfill({ json: { job_id: "job-slow", status: "running",
      stage: "resolving the venue concept", elapsed_seconds: 2,
      decision: null, error: null } });
  });
  await page.goto("/decision");
  await page.getByLabel("Venue", { exact: true }).fill("The Room");
  await page.getByLabel("Venue concept").fill("jazz");
  await page.getByLabel("Region", { exact: true }).fill("Brooklyn");
  await page.getByLabel("Audience").fill("millennials");
  await page.getByRole("button", { name: "Explore options" }).click();
  await expect(page.getByText("resolving the venue concept · 2s")).toBeVisible();
  await page.getByRole("button", { name: "Cancel decision" }).click();
  await expect(page.getByText("Cancellation requested")).toBeVisible();
  await expect(page.getByRole("button", { name: "Explore options" })).toBeEnabled();
  await expect.poll(() => cancelled).toBe(true);
});

test("agent review shows sourced proposal and leaves pilot selection to the operator", async ({ page }) => {
  const review = {
    id: "review-1", status: "recommend", snapshot_fingerprint: "fingerprint-1",
    source_mode: "live", option_id: "opt-1", venue_id: "v1", evidence_ids: ["ev-artist"],
    scenario_id: null, rationale: "Test the early set as the first pilot.",
    alternatives: [], unknowns: ["Artist availability and fee"], next_check: "Verify artist availability and fee.",
    reason: "", actions: [
      { tool: "inspect_option", arguments: { option_id: "opt-1" }, outcome: "ok", evidence_ids: ["ev-artist"], scenario_id: null },
      { tool: "check_venue", arguments: { venue_id: "v1" }, outcome: "ok", evidence_ids: [], scenario_id: null },
    ],
  };
  let saved = {
    id: "dec-review", status: "ready", source_mode: "live", snapshot_fingerprint: "fingerprint-1",
    candidates: [], options: [{ ...option, venue_ranks: { v1: 1 } }], evidence, notes: [],
    selected_option_id: null, selected_at: null, pilot_plan: null, outcome: null,
    venues: [{ id: "v1", name: "The Room", region: "Brooklyn", live_music_allowed: true, budget_limit: 500 }],
    resolution_kind: null, resolution_key: null, request: { audience: "millennials" },
    scenarios: [], agent_reviews: [] as typeof review[],
  };
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    if (url.endsWith("/api/decisions")) {
      await route.fulfill({ json: [{ id: saved.id, venue_name: "The Room", concept: "jazz", region: "Brooklyn", status: "ready", selected_option_id: null, has_outcome: false, updated_at: "2026-10-29" }] });
    } else if (url.endsWith("/agent-reviews") && route.request().method() === "POST") {
      expect(route.request().postDataJSON().snapshot_fingerprint).toBe("fingerprint-1");
      await route.fulfill({ status: 202, json: { review_id: review.id } });
    } else if (url.endsWith(`/agent-reviews/${review.id}`)) {
      saved = { ...saved, agent_reviews: [review] };
      await route.fulfill({ json: { review_id: review.id, status: "done", stage: "complete", review } });
    } else if (url.endsWith("/api/decisions/dec-review")) {
      await route.fulfill({ json: saved });
    } else {
      await route.fulfill({ status: 404, body: "Unexpected request" });
    }
  });
  await page.goto("/decision");
  await page.getByRole("button", { name: "Saved decisions" }).click();
  await page.getByRole("button", { name: /The Room.*jazz/ }).click();
  await page.getByRole("button", { name: "Review the pilot choice" }).click();
  await expect(page.getByText("Agent proposal · operator approval needed")).toBeVisible();
  await expect(page.getByText("Verify artist availability and fee.")).toBeVisible();
  await expect(page.getByRole("link", { name: /First Act · recommend/ })).toBeVisible();
  await expect(page.getByText("Selection recorded", { exact: false })).toHaveCount(0);
  await page.screenshot({ path: "test-results/agent-review.png", fullPage: true });
  await page.getByRole("button", { name: "Choose this pilot" }).click();
  await expect(page.getByLabel("Pilot venue")).toHaveValue("v1");
  await expect(page.getByLabel("Owner")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "test-results/agent-review-mobile.png", fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
