import { readFileSync } from "node:fs";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const backend = process.env.VITE_BACKEND_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    ...(process.env.FC_E2E_TLS === "true" ? {
      https: {
        key: readFileSync(process.env.FC_E2E_TLS_KEY ?? ""),
        cert: readFileSync(process.env.FC_E2E_TLS_CERT ?? ""),
      },
    } : {}),
    proxy: {
      "/api": backend,
      "/health": backend,
    },
  },
  test: {
    include: ["src/**/*.test.ts"],
  },
});
