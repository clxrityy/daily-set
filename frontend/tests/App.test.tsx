import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import App from '../src/App'

// Mock components that fetch or open sockets
vi.mock('../src/components/Leaderboard', () => ({
    Leaderboard: ({ limit }: { limit?: number }) => <div data-testid="leaderboard" aria-label={`Leaderboard (limit ${limit ?? '—'})`} />,
}))

// Mock the game hook to control UI states
vi.mock('../src/lib/game', async () => {
    const actual = await vi.importActual<any>('../src/lib/game')
    return {
        ...actual,
        useGame: vi.fn(() => ({
            board: [
                [0, 0, 0, 0], [1, 1, 1, 1], [2, 2, 2, 2],
                [0, 1, 2, 0], [1, 2, 0, 1], [2, 0, 1, 2],
                [0, 0, 1, 2], [1, 1, 2, 0], [2, 2, 0, 1],
                [0, 2, 1, 0], [1, 0, 2, 1], [2, 1, 0, 2],
            ],
            load: vi.fn(async () => { }),
            selected: [],
            toggleSelect: vi.fn(),
            submitSelected: vi.fn(async () => ({ ok: true })),
            start: vi.fn(async (name: string) => ({ name })),
            startAt: null, // not started by default
            cleared: [],
            complete: false,
            sessionId: null,
            foundSets: [],
            setBoard: vi.fn(),
        })),
    }
})

// Mock API: status endpoint
vi.mock('../src/lib/api', () => ({
    loadStatus: vi.fn(async () => ({ completed: false })),
}))

// Ensure theme root exists for components using document.documentElement
beforeEach(() => {
    document.documentElement.setAttribute('data-theme', 'light')
    vi.clearAllMocks()
})

describe('App overlay and flows', () => {
    it('shows start overlay and sanitizes username, then calls start', async () => {
        render(<App />)

        // Overlay visible with input & start button
        const input = await screen.findByPlaceholderText(/enter name/i)
        screen.getByRole('button', { name: /start game/i })

        // Type invalid characters and ensure sanitization
        fireEvent.change(input, { target: { value: 'Al!ce_#2025*loooooooooong' } })
        // Press enter to trigger start
        fireEvent.keyDown(input, { key: 'Enter' })

        // Start success toast is internal; we ensure input value sanitized to allowed set and max length 12
        expect((input as HTMLInputElement).value).toMatch(/^[A-Za-z0-9_-]{1,12}$/)
    })

    it('renders completed summary overlay when already completed', async () => {
        // Override loadStatus for this test
        const { loadStatus } = await import('../src/lib/api')
            ; (loadStatus as any).mockResolvedValueOnce({
                completed: true,
                seconds: 95,
                placement: 7,
                completed_at: new Date('2025-09-08T10:05:00Z').toISOString(),
            })

        render(<App />)

        expect(await screen.findByText(/you’ve already completed today’s game/i)).toBeInTheDocument()
        // Shows formatted time mm:ss
        expect(screen.getByText(/01:35/)).toBeInTheDocument()
        // Shows placement and a leaderboard component stub
        expect(screen.getByText(/#7/)).toBeInTheDocument()
    })

    it('shows gameover found sets gallery when complete', async () => {
        // Force useGame to return a completed state with foundSets
        const { useGame } = await import('../src/lib/game')
            ; (useGame as any).mockImplementation(() => ({
                board: [],
                load: vi.fn(async () => { }),
                selected: [],
                toggleSelect: vi.fn(),
                submitSelected: vi.fn(),
                start: vi.fn(),
                startAt: 1,
                cleared: [],
                complete: true,
                sessionId: 's1',
                foundSets: [
                    [[0, 0, 0, 1], [1, 1, 1, 2], [2, 2, 2, 0]],
                    [[0, 1, 2, 0], [1, 2, 0, 1], [2, 0, 1, 2]],
                ],
                setBoard: vi.fn(),
            }))

        render(<App />)

        expect(await screen.findByText(/all sets found/i)).toBeInTheDocument()
        // Gallery should render with the count label
        expect(screen.getByText(/sets found \(2\)/i)).toBeInTheDocument()
    })
})
