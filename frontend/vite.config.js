import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: resolve(__dirname, '../public'),
  build: {
    outDir: resolve(__dirname, '../dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(__dirname, '../public/index.html'),
      output: {
        manualChunks: {
          core: [
            resolve(__dirname, '../public/js/modules/core/state-manager.js'),
            resolve(__dirname, '../public/js/modules/core/api-service.js'),
          ],
        },
        entryFileNames: 'js/[name]-[hash].js',
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: '[ext]/[name]-[hash].[ext]',
      },
    },
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:10041',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:10041',
        ws: true,
      },
    },
  },
});
