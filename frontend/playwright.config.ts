import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:4174",
    viewport: { width: 390, height: 844 },
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4174",
    url: "http://127.0.0.1:4174",
    reuseExistingServer: true,
    env: {
      ...process.env,
      VITE_API_URL: process.env.E2E_API_URL ?? "http://localhost:8000/api",
      VITE_USE_LOCAL_FIXTURES: "false",
    },
  },
});
