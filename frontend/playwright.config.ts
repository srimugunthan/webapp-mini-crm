import { defineConfig } from "@playwright/test";

// Runs against the built SPA served by the real backend on a throwaway database.
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:8765", headless: true },
  webServer: {
    command: "rm -rf /tmp/crm-e2e && mkdir -p /tmp/crm-e2e/data && cd ../backend && DB_PATH=/tmp/crm-e2e/db/crm.sqlite DATA_DIR=/tmp/crm-e2e/data STATIC_DIR=../frontend/dist uv run uvicorn app.asgi:app --port 8765",
    url: "http://127.0.0.1:8765/api/health",
    reuseExistingServer: false,
    timeout: 60000,
  },
});
