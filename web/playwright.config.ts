import {defineConfig, devices} from "@playwright/test";

export default defineConfig({
  testDir: "./tests", fullyParallel: false, workers: 1, timeout: 60_000,
  reporter: "list", use: {baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure"},
  projects: [
    {name: "desktop", use: {...devices["Desktop Chrome"], viewport: {width: 1280, height: 900}}},
    {name: "mobile", use: {...devices["Desktop Chrome"], viewport: {width: 360, height: 800}}},
  ],
  webServer: [
    {command: "uv run --directory .. uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log", url: "http://127.0.0.1:8000/openapi.json", reuseExistingServer: false, timeout: 30_000},
    {command: "npm run start -- --port 3100", url: "http://127.0.0.1:3100", reuseExistingServer: false, timeout: 60_000},
  ],
});
