import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发环境把 API 和文件请求代理到 FastAPI (8000 端口)
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/projects': 'http://127.0.0.1:8000',
      '/notes': 'http://127.0.0.1:8000',
      '/annotations': 'http://127.0.0.1:8000',
      '/files': 'http://127.0.0.1:8000',
    },
  },
})
