import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { createReadStream, statSync } from 'node:fs'
import { resolve, sep, extname } from 'node:path'

// Repo-level artifacts/ (run evidence written by automation/). Live runs reference paths like
// "artifacts/runs/<id>/screenshots/x.png"; the backend doesn't serve files yet, so dev serves them here.
// ponytail: dev-only file server; move to a backend static route once Member 1 exposes evidence.
const ARTIFACTS = resolve(__dirname, '..', 'artifacts')
const TYPES = { '.png': 'image/png', '.json': 'application/json' }

const serveArtifacts = {
  name: 'serve-artifacts',
  configureServer(server) {
    server.middlewares.use('/artifacts', (req, res, next) => {
      let file
      try {
        file = resolve(ARTIFACTS, '.' + decodeURIComponent(req.url.split('?')[0]))
      } catch {
        return next() // malformed %-encoding
      }
      // Block path traversal and anything that isn't a known evidence type.
      if (!file.startsWith(ARTIFACTS + sep) || !TYPES[extname(file)]) return next()
      try {
        if (!statSync(file).isFile()) return next()
      } catch {
        return next()
      }
      res.setHeader('Content-Type', TYPES[extname(file)])
      createReadStream(file).pipe(res)
    })
  },
}

// Port 5180, not 5174/5175: automation/health_check.py probes those as store fallbacks.
export default defineConfig({
  plugins: [react(), serveArtifacts],
  server: {
    port: 5180,
    strictPort: true,
    // Same-origin API calls; backend URL lives only here. /api/runs -> :8000/runs
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') },
    },
  },
  preview: { port: 4180, strictPort: true },
})
