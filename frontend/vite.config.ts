import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ command }) => ({
    plugins: [react()],
    root: '.',
    base: command === 'serve' ? '/' : '/static/dist/',
    build: {
        outDir: resolve(__dirname, '../app/static/dist'),
        emptyOutDir: true,
    },
    server: {
        port: 5173,
        proxy: {
            '/api': 'http://127.0.0.1:8000',
            '/static': 'http://127.0.0.1:8000',
            '/ws': {
                target: 'ws://127.0.0.1:8000',
                ws: true
            }
        }
    }
}))
