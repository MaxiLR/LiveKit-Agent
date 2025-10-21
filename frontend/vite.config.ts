import path from "path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src")
      }
    },
    server: {
      port: Number(env.VITE_DEV_SERVER_PORT || 5173),
      host: env.VITE_DEV_SERVER_HOST || "localhost"
    },
    build: {
      outDir: "dist",
      sourcemap: true
    }
  };
});
