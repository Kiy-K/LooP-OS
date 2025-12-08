import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite Configuration.
 *
 * Configures the build tool for the React frontend, ensuring compatibility
 * with Tauri's development server and build process.
 *
 * @type {import('vite').UserConfig}
 */
export default defineConfig(async () => ({
  plugins: [react()],

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
  }
}));
