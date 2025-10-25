import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@renderer": resolve(__dirname, "src/renderer"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
