import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import { FoundSetsGallery } from '../src/components/FoundSetsGallery'
import type { Card } from '../src/lib/api'

const a: Card = [0, 0, 0, 1]
const b: Card = [1, 1, 1, 2]
const c: Card = [2, 2, 2, 0]

describe('FoundSetsGallery', () => {
    it('renders nothing for empty sets', () => {
        const { container } = render(<FoundSetsGallery sets={[]} />)
        expect(container.firstChild).toBeNull()
    })

    it('renders rows for each set and three mini-cards', () => {
        const sets: readonly Card[][] = [[a, b, c], [b, c, a]]
        render(<FoundSetsGallery sets={sets} />)
        const list = screen.getByRole('list', { name: /sets you found/i })
        expect(list).toBeInTheDocument()
        const items = screen.getAllByRole('listitem')
        expect(items.length).toBe(2)
        // Each row should contain 3 mini-cards
        items.forEach(row => {
            const minis = row.querySelectorAll('.mini-card')
            expect(minis.length).toBe(3)
        })
    })
})
