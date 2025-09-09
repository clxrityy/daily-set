import { describe, it, expect } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import React from 'react'
import { ThemeToggle } from '../src/components/ThemeToggle'

function getTheme() {
    return document.documentElement.getAttribute('data-theme')
}

describe('ThemeToggle', () => {
    it('toggles data-theme and aria-label', () => {
        const { container } = render(<ThemeToggle />)
        const btn = container.querySelector('.theme-toggle button') as HTMLButtonElement
        // initial label derived from system or stored; just ensure button exists
        expect(btn).toBeInTheDocument()

        const before = getTheme()
        fireEvent.click(btn)
        const after = getTheme()
        expect(before).not.toBe(after)

        // aria-label flips between light/dark title strings
        const label = btn.getAttribute('aria-label') || ''
        fireEvent.click(btn)
        const label2 = btn.getAttribute('aria-label') || ''
        expect(label).not.toBe(label2)
    })
})
