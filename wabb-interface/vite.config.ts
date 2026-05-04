import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Custom Vite plugin to handle saving configurations
const configurationApiPlugin = () => ({
  name: 'configuration-api',
  configureServer(server) {
    // We use express-like middleware for the Vite dev server
    server.middlewares.use(async (req, res, next) => {
      // The relative path to our python configuration JSON file
      const configPath = path.resolve(__dirname, '../data/configurations.json');

      // GET /api/configurations
      if (req.url === '/api/configurations' && req.method === 'GET') {
        try {
          const data = fs.readFileSync(configPath, 'utf-8');
          res.setHeader('Content-Type', 'application/json');
          res.end(data);
        } catch (e) {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: "Could not read configurations.json" }));
        }
        return;
      }

      // POST /api/configurations
      if (req.url === '/api/configurations' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => {
          body += chunk.toString();
        });
        req.on('end', () => {
          try {
            // Validate it's valid JSON before saving
            JSON.parse(body);
            fs.writeFileSync(configPath, body, 'utf-8');
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({ success: true }));
          } catch (e) {
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
