import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import App from '../src/App'

// Stub Leaderboard to avoid network
vi.mock('../src/components/Leaderboard', () => ({
    Leaderboard: () => <div />,
}))

// Mock the game hook to keep overlay visible
vi.mock('../src/lib/game', async () => {
    const actual = await vi.importActual<any>('../src/lib/game')
    return {
        ...actual,
        useGame: vi.fn(() => ({
            board: [],
            load: vi.fn(async () => { }),
            selected: [],
            toggleSelect: vi.fn(),
            submitSelected: vi.fn(),
            start: vi.fn(),
            startAt: null,
            cleared: [],
            complete: false,
            sessionId: null,
            foundSets: [],
            setBoard: vi.fn(),
        })),
    }
})

describe('Username prefill', () => {
    beforeEach(() => {
        localStorage.clear()
        document.documentElement.setAttribute('data-theme', 'light')
    })

    it('prefills from ds_last_username when present', async () => {
        localStorage.setItem('ds_last_username', 'Alice_2025')
        render(<App />)
        const input = await screen.findByPlaceholderText(/enter name/i)
        expect((input as HTMLInputElement).value).toBe('Alice_2025')
    })

    it('prefills from ds_session_v1.username when ds_last_username missing', async () => {
        localStorage.setItem('ds_session_v1', JSON.stringify({ username: 'Bob' }))
        render(<App />)
        const input = await screen.findByPlaceholderText(/enter name/i)
        expect((input as HTMLInputElement).value).toBe('Bob')
    })
})
