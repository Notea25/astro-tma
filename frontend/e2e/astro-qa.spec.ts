import { expect, test } from "@playwright/test";

test("fixture switch false sends the Astro QA UI to the backend", async ({ page }) => {
  const backendRequests: string[] = [];
  const apiBase = process.env.E2E_API_URL ?? "http://localhost:8000/api";
  await page.route(`${apiBase}/**`, async (route) => {
    backendRequests.push(route.request().url());
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/users/me")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 777777777,
          name: "Astro QA",
          gender: "male",
          sun_sign: "pisces",
          birth_city: "Москва, Россия",
          birth_time_known: true,
          birth_date: "2000-02-20",
          birth_time: "14:30",
          push_enabled: true,
          is_premium: true,
          created_at: "2026-07-12T00:00:00Z",
        }),
      });
      return;
    }
    await route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
  });

  await page.goto("/");
  await expect.poll(() => backendRequests.length).toBeGreaterThan(0);
  expect(backendRequests.some((url) => url.includes("/api/users/me"))).toBeTruthy();
});

test("real local backend exposes Astro QA when explicitly enabled", async ({ request }) => {
  test.skip(process.env.E2E_REAL_BACKEND !== "1", "requires seeded local Postgres/Redis");
  const base = process.env.E2E_API_URL ?? "http://localhost:8000/api";
  const response = await request.post(`${base}/users/me`);
  expect(response.ok()).toBeTruthy();
  const profile = await response.json();
  expect(profile).toMatchObject({ id: 777777777, name: "Astro QA" });
});
