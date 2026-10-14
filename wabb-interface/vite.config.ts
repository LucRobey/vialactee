import { defineConfig, type ViteDevServer } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import type { IncomingMessage, ServerResponse } from 'http'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

function getHardwareProfile(): string {
  try {
    const appConfigPath = path.resolve(__dirname, '../config/app_config.json');
    if (fs.existsSync(appConfigPath)) {
      const raw = fs.readFileSync(appConfigPath, 'utf-8');
      const cfg = JSON.parse(raw);
      return cfg.hardware_profile || 'full';
    }
  } catch {
    // fallback
  }
  return 'full';
}

function getSegmentsPath(): string {
  const profile = getHardwareProfile();
  if (profile === 'small') {
    const p = path.resolve(__dirname, '../config/segments_small.json');
    if (fs.existsSync(p)) return p;
  }
  const full = path.resolve(__dirname, '../config/segments_full.json');
  if (fs.existsSync(full)) return full;
  const legacy = path.resolve(__dirname, '../config/segments.json');
  if (fs.existsSync(legacy)) return legacy;
  return full;
}

// Custom Vite plugin to serve dynamic topology in dev mode
const topologyApiPlugin = () => ({
  name: 'topology-api',
  configureServer(server: ViteDevServer) {
    server.middlewares.use(async (req: IncomingMessage, res: ServerResponse, next: () => void) => {
      const segmentsPath = getSegmentsPath();
      const pathname = (req.url || '').split('?')[0];

      // GET /api/topology
      if (pathname === '/api/topology' && req.method === 'GET') {
        try {
          const raw = fs.readFileSync(segmentsPath, 'utf-8');
          const data = JSON.parse(raw);
          const segments: unknown[] = [];
          const cables = Array.isArray(data.cables) ? data.cables : [];
          for (const [key, value] of Object.entries(data)) {
            if (key.startsWith('segs_') && Array.isArray(value)) {
              for (const seg of value) {
                if (seg && typeof seg === 'object' && 'name' in seg) {
                  segments.push(seg);
                }
              }
            }
          }
          if (segments.length === 0 && Array.isArray(data.segments)) {
            segments.push(...data.segments);
          }
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ segments, cables }));
        } catch {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: "Could not read segments file" }));
        }
        return;
      }

      next();
    });
  }
});

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), topologyApiPlugin()],
})
