import fs from "fs";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
// Env lives in the monorepo-root .env (single source of truth shared with
// docker-compose). Only VITE_-prefixed keys are exposed to the client bundle.
// NOTE: in the dev container only apps/frontend is bind-mounted, so "../.."
// resolves outside the mount (to "/"). Watching that directory for .env
// changes causes Vite to see constant unrelated filesystem churn and loop-
// restart, so only use it when it actually exists (i.e. local, non-Docker dev).
const MONOREPO_ROOT = path.resolve(__dirname, "../..");
const envDir = fs.existsSync(path.join(MONOREPO_ROOT, ".env"))
  ? MONOREPO_ROOT
  : undefined;

// NOTE: inside the dev container "localhost" is the frontend container itself,
// so docker-compose.dev.yml points these at the core-api / TRS service names.
const CORE_API_PROXY_TARGET =
  process.env.DEV_PROXY_CORE_API_TARGET ?? "http://localhost:8000";
const TRS_PROXY_TARGET =
  process.env.DEV_PROXY_TRS_TARGET ?? "http://localhost:8001";
const SIMULATION_PROXY_TARGET =
  process.env.DEV_PROXY_SIMULATION_TARGET ?? "http://localhost:8081";

export default defineConfig({
  plugins: [react()],
  envDir,
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: CORE_API_PROXY_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/trs": {
        target: TRS_PROXY_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/trs/, ""),
      },
      "/simulation": {
        target: SIMULATION_PROXY_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/simulation/, ""),
      },
      "/uploads": {
        target: CORE_API_PROXY_TARGET,
        changeOrigin: true,
      },
    },
  },
});
