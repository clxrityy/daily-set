import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useGame } from '../src/lib/game'

// Minimal mocks for API functions used by useGame
vi.mock('../src/lib/api', () => ({
    startSession: vi.fn(async (name: string) => ({ session_id: 's1', session_token: 't1', start_ts: new Date().toISOString() })),
    submitSet: vi.fn(async () => ({ ok: true })),
    loadActiveSession: vi.fn(async () => ({ active: false })),
}))

describe('useGame hook', () => {
    beforeEach(() => {
        localStorage.clear()
    })

    it('adds and clears selections, and records found set on submit', async () => {
        const { result } = renderHook(() => useGame())

        // Seed a simple board with a valid set at 0,1,2
        act(() => {
            result.current.setBoard([
                [0, 0, 0, 0],
                [1, 1, 1, 1],
                [2, 2, 2, 2],
                [0, 1, 2, 0],
                [1, 2, 0, 1],
                [2, 0, 1, 2],
            ])
        })

        // Select three indices
        act(() => {
            result.current.toggleSelect(0)
            result.current.toggleSelect(1)
            result.current.toggleSelect(2)
        })

        // Submit should succeed and clear selection
        await act(async () => {
            await result.current.submitSelected()
        })

        expect(result.current.selected.length).toBe(0)
        expect(result.current.foundSets.length).toBe(1)
    })
})
