import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Fixed ports so the OmniSight runner always knows where the app lives.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
})
