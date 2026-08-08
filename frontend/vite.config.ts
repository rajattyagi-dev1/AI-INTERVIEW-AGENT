import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // All /api/* requests are forwarded to the FastAPI backend.
      // This avoids CORS issues during development and means the
      // frontend always calls /api/interview (never a hardcoded host).
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
