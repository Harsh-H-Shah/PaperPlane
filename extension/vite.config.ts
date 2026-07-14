import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { crx } from '@crxjs/vite-plugin'
import manifest from './manifest.config'

export default defineConfig({
  plugins: [react(), crx({ manifest })],
  build: {
    // Chrome extensions can't use inline dynamic imports across content scripts;
    // keep the target modern (MV3 runs in recent Chromium only).
    target: 'esnext',
    rollupOptions: {
      input: {
        // HTML entry points; content script + service worker come from the manifest.
        panel: 'src/panel/index.html',
        popup: 'src/popup/index.html',
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    hmr: { port: 5173 },
  },
  test: {
    globals: true,
    environment: 'node',
  },
})
