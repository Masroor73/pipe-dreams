// Plain JS on purpose: the frontend tsconfig has no Node type definitions.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

/**
 * MapLibre v6 runs its tile/geojson worker as an ES module that imports a sibling
 * chunk (maplibre-gl-shared.mjs). Its default worker URL is derived from the main
 * module's own location, which breaks once Vite pre-bundles (dev) or bundles
 * (build) the library. Serve/emit both worker files at a fixed path instead;
 * MaplibreMap.tsx points setWorkerUrl() at it (config/map.ts: MAPLIBRE_WORKER_PATH).
 * Fully offline, no CDN.
 */
const FILES = ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs'];
const DIR = 'maplibre';

export function maplibreWorker() {
  const require = createRequire(import.meta.url);
  const dist = join(dirname(require.resolve('maplibre-gl/package.json')), 'dist');
  return {
    name: 'maplibre-worker-assets',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const base = server.config.base.replace(/\/$/, '');
        const path = (req.url ?? '').split('?')[0];
        const file = FILES.find((f) => path === `${base}/${DIR}/${f}`);
        if (!file) return next();
        res.setHeader('Content-Type', 'text/javascript');
        res.end(readFileSync(join(dist, file)));
      });
    },
    generateBundle() {
      for (const f of FILES) {
        this.emitFile({ type: 'asset', fileName: `${DIR}/${f}`, source: readFileSync(join(dist, f)) });
      }
    },
  };
}
