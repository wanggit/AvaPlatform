// Vite 构建配置：启用 React 插件并保持默认开发服务器行为。
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
