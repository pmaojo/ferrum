import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import type { PluginOption } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react() as PluginOption],
  server: {
    proxy: {
      '^/api/ai': {
        target: process.env.VITE_AI_URL || 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/api\/ai/, '')
      },
      '^/api': {
        target: process.env.VITE_ENGINE_URL || 'http://localhost:3000',
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/api/, '')
      }
    }
  }
})
