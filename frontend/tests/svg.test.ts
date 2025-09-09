import { describe, it, expect } from 'vitest'
import { createSymbolSVG } from '../src/lib/svg'

describe('createSymbolSVG', () => {
    it('creates an SVG with viewBox and role', () => {
        const svg = createSymbolSVG(0, 0, 0)
        expect(svg.tagName.toLowerCase()).toBe('svg')
        expect(svg.getAttribute('viewBox')).toBe('0 0 100 100')
        expect(svg.getAttribute('role')).toBe('img')
        // has a child shape element
        expect(svg.children.length).toBeGreaterThan(0)
    })

    it('supports different shapes without throwing', () => {
        const circle = createSymbolSVG(0, 1, 2)
        const diamond = createSymbolSVG(1, 2, 1)
        const rect = createSymbolSVG(2, 0, 0)
        expect(circle.children.length).toBeGreaterThan(0)
        expect(diamond.children.length).toBeGreaterThan(0)
        expect(rect.children.length).toBeGreaterThan(0)
    })
})
