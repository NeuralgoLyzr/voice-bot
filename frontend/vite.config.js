import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // This allows the server to listen on all network interfaces
    port: 3000,        // Optional: Change the port if necessary
    open: true,         // Optional: Automatically open the browser on server start
    allowedHosts: [
      'b25f-223-185-132-49.ngrok-free.app',  // Add your ngrok host here
      'localhost',
    ],
  }
})
