import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    // Настройка прокси
    proxy: {
      // Все запросы к /api/...
      '/api': {
        // ...будут перенаправлены на ваш FastAPI бэкенд
        target: 'http://127.0.0.1:8000',
        changeOrigin: true, // необходимо для виртуальных хостов
        // Мы не переписываем путь, так как /api есть и там, и там
      },
    }
  }
})