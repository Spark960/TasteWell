import { expect, test } from "@playwright/test";

test.skip(process.env.E2E_AGENT_LIVE !== "1", "Set E2E_AGENT_LIVE=1 with a live backend to run this journey");

test("fresh Qloo decision reaches a bounded agent review in the visible workspace", async ({ page }) => {
  test.setTimeout(240_000);
  const backend = process.env.E2E_AGENT_BACKEND || "http://127.0.0.1:8000";
  await page.route("http://localhost:8000/api/**", async (route) => {
    const url = new URL(route.request().url());
    await route.continue({ url: `${backend}${url.pathname}${url.search}` });
  });
  await page.goto("/decision");
  await page.getByLabel("Venue", { exact: true }).fill("Synthetic Jazz Room");
  await page.getByLabel("Venue concept").fill("jazz club");
  await page.getByLabel("Region", { exact: true }).fill("Brooklyn, New York");
  await page.getByLabel("Audience").fill("young professionals");
  await page.getByLabel("Your artist shortlist").fill("Miles Davis\nJohn Coltrane");
  await page.getByRole("button", { name: "Explore options" }).click();
  await expect(page.getByText("Choose the intended concept tag")).toBeVisible({ timeout: 60_000 });
  await page.locator(".decision-choice.is-venue-type").first().click();
  await expect(page.getByText("Pilot options")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText(/Artist #\d within this Qloo shortlist/).first()).toBeVisible();
  await page.getByRole("button", { name: "Review the pilot choice" }).click();
  await expect(page.getByText(/Agent proposal|Agent needs input|Agent abstained/).first()).toBeVisible({ timeout: 110_000 });
  const reviewStatus = await page.locator(".decision-review-status").textContent();
  await page.getByText("What the agent checked").click();
  await expect(page.getByText(/Inspected an option and its saved Qloo rows/).first()).toBeVisible();
  await expect(page.getByText(/Checked operator venue constraints/)).toBeVisible();
  await page.screenshot({ path: "test-results/agent-review-live.png", fullPage: true });
  await page.getByRole("button", { name: "Saved decisions" }).click();
  await page.getByRole("button", { name: /Synthetic Jazz Room/ }).first().click();
  await expect(page.locator(".decision-review-status")).toHaveText(reviewStatus || "");
});
