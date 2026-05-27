import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: true,
    proxy: {
      '/auth': backendTarget,
      '/chats': backendTarget,
      '/analyze-company': backendTarget,
      '/company-analyses': backendTarget,
      '/health': backendTarget,
    },
  },
})
