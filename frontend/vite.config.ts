import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy API calls to the FastAPI backend so the browser can use
// relative paths (no CORS, no hardcoded host). In prod, set VITE_API_BASE_URL
// (read at runtime by src/api/client.ts) to the deployed API origin.
const API_TARGET = "http://localhost:8000";
const proxy = { target: API_TARGET, changeOrigin: true };

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": proxy,
      "/members": proxy,
      "/claims": proxy,
      // trailing slash: proxy /eval/run but let the SPA own bare /eval
      "/eval/": proxy,
    },
  },
});
