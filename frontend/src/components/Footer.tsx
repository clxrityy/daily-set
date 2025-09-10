import React from 'react'

function GithubIcon() {
    // GitHub mark; uses currentColor so it adapts to light/dark themes
    return (
        <svg viewBox="0 0 24 24" aria-hidden>
            <path fill="currentColor" d="M12 .5A11.5 11.5 0 0 0 .5 12.4c0 5.26 3.4 9.72 8.1 11.3.6.1.8-.26.8-.58v-2.05c-3.3.73-4-1.43-4-1.43-.55-1.4-1.34-1.77-1.34-1.77-1.1-.76.08-.74.08-.74 1.2.09 1.84 1.28 1.84 1.28 1.07 1.86 2.8 1.32 3.49 1.01.11-.79.42-1.32.76-1.63-2.64-.3-5.42-1.35-5.42-6.02 0-1.33.47-2.42 1.25-3.27-.13-.31-.54-1.56.12-3.26 0 0 1.01-.33 3.31 1.25.96-.27 1.98-.4 3-.4s2.04.13 3 .4c2.3-1.58 3.3-1.25 3.3-1.25.66 1.7.25 2.95.12 3.26.78.85 1.25 1.94 1.25 3.27 0 4.68-2.79 5.71-5.45 6 .43.37.82 1.1.82 2.23v3.3c0 .32.2.7.8.58 4.7-1.58 8.1-6.04 8.1-11.3A11.5 11.5 0 0 0 12 .5Z" />
        </svg>
    )
}

export function Footer() {
    return (
        <footer className="app-footer" role="contentinfo">
            <div className="footer-bar">
                <div className="footer-left">
                    <a className="brand" href="/" aria-label="Daily Set home" title="Daily Set">
                        <img className="brand-logo" src="/static/favicon-32x32.png" alt="Logo" />
                        <span className="brand-title">Daily Set</span>
                    </a>
                </div>
                <div className="footer-right">
                    <a
                        className="footer-btn"
                        href="https://github.com/clxrityy/daily-set"
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label="Open GitHub repository"
                        title="GitHub"
                    >
                        <GithubIcon />
                    </a>
                </div>
            </div>
        </footer>
    )
}
