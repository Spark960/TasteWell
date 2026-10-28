import { expect, test } from "@playwright/test";

test.skip(process.env.E2E_LIVE !== "1", "Set E2E_LIVE=1 to call the real local backend and Qloo");

test("real Qloo resolves a public artist shortlist and ranks two venues", async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto("/decision");
  await page.getByLabel("Venue", { exact: true }).fill("Tastewell live test room");
  await page.getByLabel("Venue concept").fill("jazz");
  await page.getByLabel("Region").fill("Brooklyn, New York");
  await page.getByLabel("Audience").fill("millennials");
  await page.getByRole("button", { name: "Add venue" }).click();
  await page.getByLabel("Venue name").last().fill("Tastewell live test second room");
  await page.getByLabel("Region").last().fill("Queens, New York");
  await page.getByLabel("Your artist shortlist").fill("Miles Davis\nJohn Coltrane");
  await page.getByRole("button", { name: "Explore options" }).click();
  await expect(page.getByText("Choose the intended concept tag")).toBeVisible({ timeout: 45_000 });
  await page.getByRole("button", { name: /Jazz.*genre:music/i }).first().click();
  for (let i = 0; i < 2; i += 1) {
    const artistPrompt = page.getByText(/Choose the intended artist for/);
    const ready = page.getByText("Pilot options");
    await expect(artistPrompt.or(ready)).toBeVisible({ timeout: 60_000 });
    if (await ready.isVisible()) break;
    const name = (await artistPrompt.textContent())?.replace("Choose the intended artist for ", "").trim();
    await page.getByRole("button", { name: new RegExp(`^${name} artist$`, "i") }).first().click();
  }
  await expect(page.getByText("Pilot options")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/Pilot an early set with/)).toBeVisible();
  await page.getByText("Inspect Qloo evidence").first().click();
  await expect(page.getByText(/Correlation:/).first()).toBeVisible();
  await expect(page.getByText(/Artist #\d within this Qloo shortlist/).first()).toBeVisible();
  await expect(page.getByText("Venue comparison · rank within each separate call").first()).toBeVisible();
  await expect(page.getByText(/Tastewell live test room: artist #\d/).first()).toBeVisible();
  await expect(page.getByText(/Tastewell live test second room: artist #\d/).first()).toBeVisible();
  await page.getByLabel("Scenario audience").fill("young professionals");
  await page.getByRole("button", { name: "Compare scenario" }).click();
  await expect(page.getByText("Inspect scenario queries and evidence")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/Rank positions compare the same artist IDs within each call/)).toBeVisible();
});
