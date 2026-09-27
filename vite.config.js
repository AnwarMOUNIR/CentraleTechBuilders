import { defineConfig } from "vite";

export default defineConfig({
  root: "web",
  server: {
    proxy: {
      "/interpret": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000"
    }
  },
  build: {
    outDir: "../dist",
    emptyOutDir: true
  }
});
