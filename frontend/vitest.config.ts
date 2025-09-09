import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    test: {
        include: ['tests/**/*.test.ts', 'tests/**/*.test.tsx'],
        environment: 'jsdom',
        globals: true,
        setupFiles: './vitest.setup.ts',
        coverage: {
            provider: 'v8',
            reporter: ['text', 'html', 'lcov'],
        },
    },
})
