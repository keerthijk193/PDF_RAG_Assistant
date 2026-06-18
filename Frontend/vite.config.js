// vite.config.js
// =============================================================================
// Vite is our "build tool" — it:
//   1. Serves files during development (with hot reload)
//   2. Bundles and optimizes files for production
//
// WHY VITE OVER CREATE-REACT-APP?
//   Vite is much faster because it uses ES modules natively in development,
//   instead of bundling everything first. Cold starts are near-instant.
// =============================================================================

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [
    react(), // Transforms JSX into regular JavaScript
  ],

  server: {
    port: 5173, // The port React dev server runs on
    
    // Proxy: forward /api/* requests to FastAPI
    // This avoids CORS issues during development
    // (Optional — we handle CORS in FastAPI directly, but useful to know)
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
