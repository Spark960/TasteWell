import { expect, test } from "@playwright/test";

type Ev = Record<string, unknown>;

function ts(i: number): string {
  return `2026-10-21T12:00:0${i}Z`;
}

function sse(events: Ev[]): string {
  return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
}

function groundedOkEvents(): Ev[] {
  const brief = {
    audience_profile: "People in this area tend to favor low-key bars (id:urn:tag:genre:jazz)",
    menu_tilt: ["Omakase-style small plates (id:urn:tag:thing:omakase)"],
    music_programming: ["Vinyl jazz nights (id:urn:tag:genre:jazz)"],
    adjacent_brands: ["Local craft roasters (id:urn:tag:brand:craft-roaster)"],
    tag_themes: ["jazz — urn:tag:genre:jazz"],
    honest_absences: ["audience_demographics"],
    evidence: [
      {
        tool: "qloo_find_tags",
        operation: "find_tags",
        status: "ok",
        summary: "resolved 3 candidate tags for jazz",
        ids: ["urn:tag:genre:jazz"],
        result_count: 3,
      },
    ],
  };
  return [
    { ts: ts(1), type: "run_started", mode: "grounded", brief: "listening bar", region: "Williamsburg", audience: "young professionals" },
    { ts: ts(2), type: "status", message: "readiness_ok", mode: "mcp", tools: ["qloo_find_tags"] },
    { ts: ts(3), type: "tool_call", tool: "qloo_find_tags", args: { query: "jazz" } },
    { ts: ts(4), type: "tool_result", tool: "qloo_find_tags", status: "ok", result_count: 3, summary: "resolved jazz tags", candidates: [] },
    { ts: ts(5), type: "llm", step: 1, tool_calls: ["qloo_find_tags"] },
    { ts: ts(6), type: "final", brief },
    { ts: ts(7), type: "run_done", exit_status: "ok", run_status: "done", error: null },
  ];
}

function genericOkEvents(): Ev[] {
  return [
    { ts: ts(1), type: "run_started", mode: "generic", brief: "listening bar", region: "Williamsburg", audience: "young professionals" },
    { ts: ts(2), type: "llm", step: 1 },
    {
      ts: ts(3),
      type: "final",
      brief: {
        audience_profile: "Young professionals generally enjoy social evenings.",
        menu_tilt: ["Shareable plates (a guess)"],
        music_programming: ["DJ sets (a guess)"],
        adjacent_brands: ["Trendy seltzer brands (a guess)"],
        tag_themes: [],
        honest_absences: [],
      },
    },
    { ts: ts(4), type: "run_done", exit_status: "ok", run_status: "done", error: null },
  ];
}

function needsInputEvents(): Ev[] {
  return [
    { ts: ts(1), type: "run_started", mode: "grounded", brief: "listening bar", region: "Williamsburg", audience: "" },
    { ts: ts(2), type: "tool_call", tool: "qloo_describe", args: { entity: "Williamsburg" } },
    { ts: ts(3), type: "tool_result", tool: "qloo_describe", status: "needs_input", result_count: 0, summary: "ambiguous name", candidates: [] },
    { ts: ts(4), type: "final", brief: {} },
    { ts: ts(5), type: "run_done", exit_status: "needs_input", run_status: "done", error: null },
  ];
}

const LOCALITIES = [
  { id: "urn:locality:williamsburg-bk", name: "Williamsburg", type: "locality", popularity: 0.82 },
  { id: "urn:locality:williamsburg-va", name: "Williamsburg", type: "locality", popularity: 0.11 },
];

test.describe("tastewell smoke (mocked backend)", () => {
  let groundedPostCount = 0;
  test.beforeEach(async () => {
    groundedPostCount = 0;
  });
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/agent/run", async (route) => {
      const body = route.request().postDataJSON() as { mode: string };
      let runId: string;
      if (body.mode === "grounded") {
        groundedPostCount += 1;
        runId = `g-run-${groundedPostCount}`;
      } else {
        runId = "u-run-1";
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: runId,
          status: "queued",
          mode: body.mode,
          stream_url: `/api/agent/stream/${runId}`,
        }),
      });
    });
    await page.route("**/api/agent/runs/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: "g-run-1",
          status: "done",
          exit_status: "needs_input",
          needs_input: {
            reason: "Williamsburg matches several locality entities — pick one.",
            candidates: LOCALITIES,
          },
          brief: null,
          events: 5,
        }),
      });
    });
    await page.route("**/api/agent/stream/**", async (route) => {
      const url = route.request().url();
      if (url.includes("u-run")) {
        await route.fulfill({
          status: 200,
          contentType: "text/event-stream",
          body: sse(genericOkEvents()),
        });
        return;
      }
      // grounded: the pick re-drive uses g-run-2 → ok brief; first run → needs_input
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: sse(url.includes("g-run-2") ? groundedOkEvents() : needsInputEvents()),
      });
    });
  });

  test("preset click → both panes render; trace shows tool rows", async ({ page }) => {
    await page.goto("/");
    await page
      .getByRole("button", { name: "Wine bar" })
      .click();
    // To exercise the ok path without the picker branch, the first grounded
    // stream would serve needs_input — so this spec picks it immediately and
    // the pick re-drive lands on g-run-2 (ok brief). Wait for the picker:
    await page.getByRole("button", { name: "Run both panes" }).click();

    const gPane = page.getByRole("region", { name: "Grounded result", exact: true });
    await expect(
      gPane.getByRole("dialog", { name: "Disambiguation picker" }),
    ).toBeVisible();
    await gPane
      .getByRole("button", { name: /Williamsburg/ })
      .first()
      .click();

    await expect(gPane).toContainText("Omakase-style small plates");
    await expect(gPane).toContainText("No grounded result");

    const uPane = page.getByRole("region", { name: "Ungrounded result", exact: true });
    await expect(uPane).toContainText("model's own guesses");
    await expect(uPane).toContainText("Shareable plates");
  });

  test("needs_input → picker → pick re-drives grounded pane to done", async ({ page }) => {
    await page.goto("/");
    await page
      .getByRole("button", { name: "Listening bar" })
      .click();
    await page.getByRole("button", { name: "Run both panes" }).click();

    const gPane = page.getByRole("region", { name: "Grounded result", exact: true });
    await expect(gPane).toContainText(
      "Williamsburg matches several locality entities",
    );
    await gPane
      .getByRole("button", { name: /Williamsburg/ })
      .first()
      .click();

    // re-drive: grounded run 2 streams the ok brief
    await expect(gPane).toContainText("Omakase-style small plates");
    await expect(gPane).toContainText("find_tags");
  });

  test("trace panel lists tool rows with status chips", async ({ page }) => {
    await page.goto("/");
    await page
      .getByRole("button", { name: "Tacos" })
      .click();
    await page.getByRole("button", { name: "Run both panes" }).click();

    const traceToggle = page.getByRole("button", { name: /Live trace/ });
    await expect(traceToggle).toContainText("events");
    // panel auto-opens once events exist; only click if it isn't open already
    if ((await traceToggle.getAttribute("aria-expanded")) !== "true") {
      await traceToggle.click();
    }
    await page.getByRole("button", { name: "tools", exact: true }).click();
    await expect(page.getByText("qloo_describe").first()).toBeVisible();
    // needs_input status chip color-coded in the trace
    await expect(
      page.getByRole("region", { name: "Live trace panel" }).getByText("needs_input").first(),
    ).toBeVisible();
  });
});
