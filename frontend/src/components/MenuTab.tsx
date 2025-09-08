import React from 'react'
import { ThemeToggle } from './ThemeToggle'

function TrophyIcon() {
    return (
        <svg viewBox="0 0 24 24" aria-hidden>
            <path fill="currentColor" d="M7 3h10a1 1 0 0 1 1 1v1h2a1 1 0 0 1 1 1c0 3.5-2.2 6-5 6a7 7 0 0 1-4 2.7V18h3a1 1 0 1 1 0 2H9a1 1 0 1 1 0-2h3v-2.3A7 7 0 0 1 8 12C5.2 12 3 9.5 3 6a1 1 0 0 1 1-1h2V4a1 1 0 0 1 1-1Zm11 3V6h-1V5H7v1H6v1c0 2.7 1.8 4 3 4h6c1.2 0 3-1.3 3-4ZM5 7c0 1.6.6 2.7 1.4 3.3c.5.4 1.2.7 1.6.7H8c-.8-.9-1-2.2-1-4H5Zm14 0h-2c0 1.8-.3 3.1-1 4h.1c.4 0 1.1-.3 1.6-.7C18.4 9.7 19 8.6 19 7Z" />
        </svg>
    )
}

export function MenuTab({ onOpenLeaderboard }: { readonly onOpenLeaderboard: () => void }) {
    return (
        <div className="menu-tab" role="region" aria-label="Menu">
            <div className="menu-inner">
                {/* Embed theme toggle button without changing its logic */}
                <div className="menu-item" aria-label="Theme">
                    <ThemeToggle />
                </div>
                <button type="button" className="menu-btn" aria-label="Open leaderboard" title="Leaderboard" onClick={onOpenLeaderboard}>
                    <TrophyIcon />
                </button>
            </div>
        </div>
    )
}
