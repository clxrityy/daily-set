import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import { Board } from '../src/components/Board'
import type { Card } from '../src/lib/api'

const c: Card = [0, 0, 0, 1]
const d: Card = [1, 1, 1, 2]
const e: Card = [2, 2, 2, 3]

describe('Board', () => {
    it('renders a grid of CardView and forwards clicks', () => {
        const onSelect = vi.fn()
        render(<Board board={[c, d, e]} selected={[1]} onSelect={onSelect} cleared={new Set([2])} preStart={false} gameOver={false} />)

        const cards = screen.getAllByRole('button')
        expect(cards.length).toBe(3)
        // Click first
        fireEvent.click(cards[0])
        expect(onSelect).toHaveBeenCalledWith(0)
    })

    it('is inert when preStart or gameOver', () => {
        const onSelect = vi.fn()
        const { rerender } = render(<Board board={[c, d]} selected={[]} onSelect={onSelect} preStart={true} gameOver={false} />)
        fireEvent.click(screen.getAllByRole('button')[0])
        expect(onSelect).not.toHaveBeenCalled()

        rerender(<Board board={[c, d]} selected={[]} onSelect={onSelect} preStart={false} gameOver={true} />)
        fireEvent.click(screen.getAllByRole('button')[0])
        expect(onSelect).not.toHaveBeenCalled()
    })
})
