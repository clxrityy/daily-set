import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import { LeaderboardPanel } from '../src/components/LeaderboardPanel'

// Mock Leaderboard to avoid real data fetching and websockets
vi.mock('../src/components/Leaderboard', () => ({
    Leaderboard: ({ limit }: { limit?: number }) => (
        <div data-testid="leaderboard" aria-label={`Leaderboard list (limit ${limit ?? '—'})`} />
    ),
}))

describe('LeaderboardPanel', () => {
    it('renders when open and closes via backdrop click', () => {
        const onClose = vi.fn()
        const { container } = render(<LeaderboardPanel open={true} onClose={onClose} />)

        expect(screen.getByRole('complementary', { name: /leaderboard panel/i })).toBeInTheDocument()
        // Backdrop is aria-hidden; query via selector
        const backdrop = container.querySelector('.side-backdrop') as HTMLElement
        expect(backdrop).toBeTruthy()
        fireEvent.click(backdrop)
        expect(onClose).toHaveBeenCalled()
    })

    it('closes on Escape key', () => {
        const onClose = vi.fn()
        render(<LeaderboardPanel open={true} onClose={onClose} />)

        fireEvent.keyDown(window, { key: 'Escape' })
        expect(onClose).toHaveBeenCalled()
    })

    it('switches tabs and shows stub content', () => {
        const onClose = vi.fn()
        render(<LeaderboardPanel open={true} onClose={onClose} />)

        // Daily tab active by default -> shows mocked Leaderboard
        expect(screen.getByTestId('leaderboard')).toBeInTheDocument()

        // Switch to Weekly
        fireEvent.click(screen.getByRole('button', { name: /weekly/i }))
        expect(screen.getByText(/weekly leaderboard coming soon/i)).toBeInTheDocument()

        // Switch to Monthly
        fireEvent.click(screen.getByRole('button', { name: /monthly/i }))
        expect(screen.getByText(/monthly leaderboard coming soon/i)).toBeInTheDocument()

        // Back to Daily
        fireEvent.click(screen.getByRole('button', { name: /daily/i }))
        expect(screen.getByTestId('leaderboard')).toBeInTheDocument()
    })
})
