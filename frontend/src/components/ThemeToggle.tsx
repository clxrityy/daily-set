import React, { useEffect, useState } from 'react'

function SunIcon({ active }: { readonly active: boolean }) {
    return (
        <svg viewBox="0 0 24 24" aria-hidden className={active ? 'icon-active' : 'icon-enter'}>
            <circle cx="12" cy="12" r="4" fill="currentColor" />
            {Array.from({ length: 8 }).map((_, i) => {
                const a = (i * Math.PI) / 4
                const x1 = 12 + Math.cos(a) * 7
                const y1 = 12 + Math.sin(a) * 7
                const x2 = 12 + Math.cos(a) * 10.5
                const y2 = 12 + Math.sin(a) * 10.5
                const key = `${x1}-${y1}-${x2}-${y2}`
                return <line key={key} x1={x1} y1={y1} x2={x2} y2={y2} stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            })}
        </svg>
    )
}

function MoonIcon({ active }: { readonly active: boolean }) {
    return (
        <svg viewBox="0 0 24 24" aria-hidden className={active ? 'icon-active' : 'icon-enter'}>
            <path fill="currentColor" d="M 15.5 2.5 c -4.6 0 -8.3 3.7 -8.3 8.3 s 3.7 8.3 8.3 8.3 c 2.6 0 5 -1.2 6.5 -3.1 c -1.2 0.5 -2.4 0.7 -3.7 0.5 c -3.6 -0.6 -6.3 -3.9 -6.3 -7.5 c 0 -1.3 0.3 -2.5 0.9 -3.6 c 0.2 -0.3 0.3 -0.6 0.3 -0.9 c 0 -1.2 -1 -2 -1.7 -2 c -0.1 0 -0.2 0 -0.3 0 z" />
        </svg>
    )
}

function getSystemPref(): 'light' | 'dark' {
    if (typeof window === 'undefined') return 'light'
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function loadPref(): 'light' | 'dark' | null {
    if (typeof window === 'undefined') return null
    const v = localStorage.getItem('theme')
    return v === 'light' || v === 'dark' ? v : null
}

function savePref(theme: 'light' | 'dark') {
    try { localStorage.setItem('theme', theme) } catch { }
}

export function ThemeToggle() {
    const [theme, setTheme] = useState<'light' | 'dark'>(() => loadPref() ?? getSystemPref())

    const isDark = theme === 'dark'

    // Apply to documentElement and a helper class on body (for app.css scoping)
    useEffect(() => {
        const root = document.documentElement
        const body = document.body
        root.setAttribute('data-theme', theme)
        body.classList.add('theme-vars')
        savePref(theme)
    }, [theme])

    // React to system theme changes if user hasn’t set a manual preference
    useEffect(() => {
        if (loadPref() != null) return
        const mql = window.matchMedia('(prefers-color-scheme: dark)')
        const handler = (e: MediaQueryListEvent) => setTheme(e.matches ? 'dark' : 'light')
        mql.addEventListener('change', handler)
        return () => mql.removeEventListener('change', handler)
    }, [])

    const title = isDark ? 'Switch to light mode' : 'Switch to dark mode'

    return (
        <div className="theme-toggle">
            <button
                type="button"
                aria-label={title}
                title={title}
                onClick={() => setTheme(isDark ? 'light' : 'dark')}
            >
                {/* Crossfade/rotate via CSS classes, no inline styles */}
                <div className="icon-wrap">
                    <div className={`icon-layer ${isDark ? 'hide' : 'show'}`}>
                        <SunIcon active={!isDark} />
                    </div>
                    <div className={`icon-layer ${isDark ? 'show' : 'hide'}`}>
                        <MoonIcon active={isDark} />
                    </div>
                </div>
            </button>
        </div>
    )
}
