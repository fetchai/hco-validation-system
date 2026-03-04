import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),tailwindcss(),],
  server: {
    port: 5173, // Ensure consistent port
    host: 'localhost',
    headers: {
      // Fix COOP/COEP issues for MSAL authentication
      'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
      'Cross-Origin-Embedder-Policy': 'unsafe-none'
    },
    // proxy: {
    //   '/api': {
    //     target: 'http://localhost:8096',
    //     changeOrigin: true,
    //     secure: false,
    //     rewrite: (path: string) => path.replace(/^\/api/, '')
    //   }
    // }
  }
})
