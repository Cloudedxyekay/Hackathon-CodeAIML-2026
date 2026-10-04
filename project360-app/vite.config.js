import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    watch: {
      // Avoid native file-watch errors in OneDrive-synchronized folders.
      usePolling: true,
      interval: 500
    },
    proxy: {
      "/api": "http://127.0.0.1:8000"
    }
  }
});

