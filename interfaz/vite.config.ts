import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Se construye dentro del paquete de Python (estudio/web_app) y Xandart la sirve en /app.
// En desarrollo (npm run dev) las llamadas a la API van al Xandart local del puerto 8030.
export default defineConfig({
  base: '/app/',
  plugins: [react()],
  build: { outDir: '../estudio/web_app', emptyOutDir: true },
  server: {
    proxy: { '/api': 'http://127.0.0.1:8030', '/archivos': 'http://127.0.0.1:8030' },
  },
});
