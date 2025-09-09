import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { Leaderboard } from '../src/components/Leaderboard'

vi.mock('../src/lib/api', () => ({
    loadLeaderboard: vi.fn(async () => ({
        date: '2025-09-08', leaders: [
            { username: 'alice', best: 75, completed_at: new Date().toISOString() },
            { username: 'bob', best: 90, completed_at: new Date().toISOString() },
        ]
    })),
    loadFoundSets: vi.fn(async () => ({
        sets: [
            [[0, 0, 0, 1], [1, 1, 1, 2], [2, 2, 2, 0]],
        ]
    })),
}))

describe('Leaderboard', () => {
    beforeEach(() => {
        // mock WebSocket to avoid real connections
        // @ts-expect-error
        global.WebSocket = class { constructor() { } close() { } onopen: any; onmessage: any; onerror: any; onclose: any }
    })

    it('renders table and opens user sets panel', async () => {
        render(<Leaderboard limit={10} />)

        // Shows table rows
        const rows = await screen.findAllByRole('row')
        expect(rows.length).toBeGreaterThan(1)

        // Click on first username to open sets panel
        const btn = await screen.findByRole('button', { name: /view sets found by alice/i })
        fireEvent.click(btn)

        await waitFor(() => {
            expect(screen.getByRole('region', { name: /sets found by alice/i })).toBeInTheDocument()
        })
    })
})
