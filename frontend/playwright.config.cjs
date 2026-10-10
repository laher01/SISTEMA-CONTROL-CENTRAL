const tls = process.env.FC_E2E_TLS === "true";
const protocol = tls ? "https" : "http";

module.exports = {
  testDir: "./e2e",
  use: { baseURL: `${protocol}://127.0.0.1:4173`, headless: true, ignoreHTTPSErrors: tls },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4173 --strictPort",
    url: `${protocol}://127.0.0.1:4173`,
    reuseExistingServer: false,
    ignoreHTTPSErrors: tls,
    timeout: 30000,
  },
};
