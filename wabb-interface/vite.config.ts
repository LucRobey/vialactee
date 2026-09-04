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

function getConfigurationsPath(): string {
  const profile = getHardwareProfile();
  if (profile === 'small') {
    const p = path.resolve(__dirname, '../data/configurations_small.json');
    if (fs.existsSync(p)) return p;
  }
  const full = path.resolve(__dirname, '../data/configurations_full.json');
  if (fs.existsSync(full)) return full;
  return path.resolve(__dirname, '../data/configurations.json');
}

// Custom Vite plugin to handle saving configurations
const configurationApiPlugin = () => ({
  name: 'configuration-api',
  configureServer(server: ViteDevServer) {
    // We use express-like middleware for the Vite dev server
    server.middlewares.use(async (req: IncomingMessage, res: ServerResponse, next: () => void) => {
      const configPath = getConfigurationsPath();
      const segmentsPath = getSegmentsPath();

      // GET /api/configurations
      if (req.url === '/api/configurations' && req.method === 'GET') {
        try {
          const data = fs.readFileSync(configPath, 'utf-8');
          res.setHeader('Content-Type', 'application/json');
          res.end(data);
        } catch {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: "Could not read configurations file" }));
        }
        return;
      }

      // GET /api/topology
      if (req.url === '/api/topology' && req.method === 'GET') {
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

      // POST /api/configurations
      if (req.url === '/api/configurations' && req.method === 'POST') {
        let body = '';
        req.on('data', (chunk: Buffer) => {
          body += chunk.toString();
        });
        req.on('end', () => {
          try {
            // Validate it's valid JSON before saving
            const data = JSON.parse(body);
            if (
              !data ||
              !data.configurations ||
              typeof data.configurations !== 'object' ||
              Array.isArray(data.configurations)
            ) {
              throw new Error('Invalid configurations schema');
            }
            const sanitized = { configurations: data.configurations };
            fs.writeFileSync(configPath, `${JSON.stringify(sanitized, null, 2)}\n`, 'utf-8');
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ success: true }));
          } catch {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: "Invalid JSON provided" }));
          }
        });
        return;
      }

      next();
    });
  }
});

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), configurationApiPlugin()],
})
