/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { maplibreWorker } from './vite-plugins/maplibre-worker.mjs';

export default defineConfig({
  plugins: [react(), maplibreWorker()],
  server: { port: 5173 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Only the two global stylesheets are processed in tests (read raw by the reduced-motion policy test).
    css: { include: [/src[\\/]styles[\\/](global|tokens)\.css/] },
    env: { VITE_USE_FIXTURES: 'true' },
  },
});
