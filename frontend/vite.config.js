import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // 核心：开发时前端请求 /api 自动转发到后端 FastAPI，避免跨域
    // 生产环境则由 Nginx 完成同样的转发（见 4.8 节 nginx.conf）
    proxy: {
      '/api': {
        target: 'http://localhost:8000',   // 后端 FastAPI 地址
        changeOrigin: true
      },
      // 原生监控 iframe 也需要代理（开发环境调试用）
      '/grafana': { target: 'http://localhost:3000', changeOrigin: true },
      '/prometheus': { target: 'http://localhost:9090', changeOrigin: true },
      '/loki': { target: 'http://localhost:3100', changeOrigin: true }
    }
  },
  build: {
    outDir: 'dist'
  }
})
