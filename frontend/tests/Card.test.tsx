import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import { CardView } from '../src/components/Card'
import type { Card as TCard } from '../src/lib/api'

const card: TCard = [0, 1, 2, 3]

describe('CardView', () => {
    it('renders button-like card with symbols and toggles on click', () => {
        const onSelect = vi.fn()
        render(<CardView card={card} idx={0} selected={false} onSelect={onSelect} cleared={false} preStart={false} />)

        const btn = screen.getByRole('button', { name: /card 1/i })
        expect(btn).toBeInTheDocument()
        // Appends count symbols (3)
        const symbols = btn.querySelectorAll('.symbols svg')
        expect(symbols.length).toBe(3)

        fireEvent.click(btn)
        expect(onSelect).toHaveBeenCalledWith(0)
    })

    it('is inert when cleared or preStart', () => {
        const onSelect = vi.fn()
        const { rerender } = render(<CardView card={card} idx={1} selected={false} onSelect={onSelect} cleared={true} preStart={false} />)
        const btn = screen.getByRole('button', { name: /card 2/i })
        fireEvent.click(btn)
        expect(onSelect).not.toHaveBeenCalled()

        rerender(<CardView card={card} idx={2} selected={false} onSelect={onSelect} cleared={false} preStart={true} />)
        const btn2 = screen.getByRole('button', { name: /card 3/i })
        fireEvent.click(btn2)
        expect(onSelect).not.toHaveBeenCalled()
    })
})
