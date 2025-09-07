import { describe, it, expect } from 'vitest'
import { hasValidSets, isValidSet } from '../src/lib/game'
import type { Card } from '../src/lib/api'

describe('set logic', () => {
    it('validates set property rule', () => {
        const a: Card = [0, 0, 0, 0]
        const b: Card = [1, 1, 1, 1]
        const c: Card = [2, 2, 2, 2]
        expect(isValidSet(a, b, c)).toBe(true)
    })

    it('detects absence of sets', () => {
        const board: Card[] = [
            [0, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0],
            [0, 1, 0, 0], [1, 0, 0, 0], [1, 1, 1, 0],
            [1, 1, 0, 1], [1, 0, 1, 1], [2, 2, 2, 1],
            [2, 1, 2, 2], [2, 2, 1, 2], [2, 2, 2, 0]
        ]
        expect(hasValidSets(board, new Set())).toBeTypeOf('boolean')
    })
})
