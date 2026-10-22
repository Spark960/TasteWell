import { expect, test } from "@playwright/test";

// Live end-to-end drive against the REAL backend (:8000).
// Opt-in only: E2E_LIVE=1 npx playwright test e2e/live.spec.ts
// Burns grounded + generic runs (~2× 8 LLM requests, ~10 Qloo tool calls).
test.skip(!process.env.E2E_LIVE, "opt-in: set E2E_LIVE=1 to hit the real backend");

test("live local demo: preset → needs_input → pick → grounded ok brief", async ({ page }) => {
  test.setTimeout(300_000);
  await page.goto("/");

  await page
    .getByRole("button", { name: "Listening bar · young professionals · Williamsburg" })
    .click();
  await page.getByRole("button", { name: "Run both panes" }).click();

  const gPane = page.getByRole("region", { name: "Grounded result", exact: true });
  const uPane = page.getByRole("region", { name: "Ungrounded result", exact: true });

  // Terminal state #1: picker (needs_input) OR brief sections OR honest alert.
  await expect(async () => {
    const hits =
      (await gPane.getByRole("dialog", { name: "Disambiguation picker" }).count()) +
      (await gPane.getByRole("heading", { level: 3 }).count()) +
      (await gPane.getByRole("alert").count());
    expect(hits).toBeGreaterThan(0);
  }).toPass({ timeout: 280_000 });

  // If ambiguous (the live norm for place names like "Williamsburg"),
  // exercise the D12 headline: pick a candidate → re-drive → ok brief.
  const picker = gPane.getByRole("dialog", { name: "Disambiguation picker" });
  if (await picker.isVisible().catch(() => false)) {
    await picker.getByRole("button").first().click();
    await expect(gPane.getByRole("heading", { name: "Tag themes" }))
      .toBeVisible({ timeout: 280_000 });
  }

  // Ungrounded pane must reach a terminal state too.
  await expect(async () => {
    const hits =
      (await uPane.getByRole("heading", { level: 3 }).count()) +
      (await uPane.getByRole("alert").count());
    expect(hits).toBeGreaterThan(0);
  }).toPass({ timeout: 280_000 });
});
