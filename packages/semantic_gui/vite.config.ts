import path from 'path';

import runtimeErrorOverlay from '@replit/vite-plugin-runtime-error-modal';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [
    react(),
    runtimeErrorOverlay(),
    ...(process.env.NODE_ENV !== 'production' &&
    process.env.REPL_ID !== undefined
      ? [
          await import('@replit/vite-plugin-cartographer').then(m =>
            m.cartographer()
          ),
        ]
      : []),
  ],
  server: {
    hmr: {
      port: 24678,
      clientPort: 24678,
      overlay: false, // Disable error overlay that might cause WebSocket issues
    },
    ws: {
      port: 24678,
    },
    host: '0.0.0.0', // Ensure it binds to all interfaces
  },
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, 'client', 'src'),
      '@shared': path.resolve(import.meta.dirname, 'shared'),
      '@assets': path.resolve(import.meta.dirname, 'attached_assets'),
    },
  },
  root: path.resolve(import.meta.dirname, 'client'),
  build: {
    outDir: path.resolve(import.meta.dirname, 'dist/client'),
    emptyOutDir: true,
  },
});
