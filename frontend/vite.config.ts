import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "IGNIS_");
  const proxy = { "/api": { target: env.IGNIS_API_PROXY || "http://127.0.0.1:8765", changeOrigin: false,
    rewrite: (path: string) => path.replace(/^\/api/, ""), timeout: 300_000, proxyTimeout: 300_000 } };
  return { plugins: [react(), tailwindcss()], server: { proxy }, preview: { proxy } };
});
