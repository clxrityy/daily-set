import React, { useEffect, useMemo, useState } from 'react'
import { Board } from './components/Board'
import { ToastProvider, useToasts } from './lib/errors'
import { useGame } from './lib/game'
import { Leaderboard } from './components/Leaderboard'
import { loadStatus } from './lib/api'
import { MenuTab } from './components/MenuTab'
import { LeaderboardPanel } from './components/LeaderboardPanel'
import { FoundSetsGallery } from './components/FoundSetsGallery'
// import type { Card } from './lib/api'

const SKELETON_KEYS: readonly string[] = Array.from({ length: 12 }, (_, i) => `s-${i}`)
// CardView moved to components/Card

// Set previews temporarily removed; can be re-enabled later.

function InnerApp() {
    const { board, load, selected, toggleSelect, submitSelected, start, startAt, cleared, complete, sessionId, foundSets } = useGame()
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [username, setUsername] = useState('')
    const [elapsed, setElapsed] = useState(0)
    const toasts = useToasts()
    const [completedToday, setCompletedToday] = useState<boolean | null>(null)
    const [completedDetail, setCompletedDetail] = useState<{ seconds?: number; placement?: number; completed_at?: string | null } | null>(null)
    // Set previews temporarily removed

    const formatSeconds = (secs?: number) => {
        if (secs == null) return '—'
        const m = Math.floor(secs / 60).toString().padStart(2, '0')
        const s = (secs % 60).toString().padStart(2, '0')
        return `${m}:${s}`
    }

    const todayLabel = useMemo(() => new Date().toLocaleDateString(undefined, {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    }), [])

    // Initial load: attempt restore only; do not fetch daily board until started
    useEffect(() => {
        let alive = true
        load()
            .catch((e) => { if (alive) setError(String(e)) })
            .finally(() => { if (alive) setLoading(false) })
        return () => { alive = false }
    }, [load])

    // Load completion status
    useEffect(() => {
        let alive = true
        loadStatus()
            .then((status) => {
                if (!alive) return
                setCompletedToday(!!status.completed)
                if (status.completed) {
                    setCompletedDetail({ seconds: status.seconds, placement: status.placement, completed_at: status.completed_at })
                }
            })
            .catch(() => { if (alive) setCompletedToday(false) })
        return () => { alive = false }
    }, [])

    useEffect(() => {
        if (selected.length === 3) {
            submitSelected().then((res: any) => {
                if (res?.ok) toasts.add({ severity: 'success', message: 'Great! Valid set found!' })
                else if (res?.userFriendly) toasts.add({ severity: 'info', message: res.data.detail })
                else toasts.add({ severity: 'error', message: 'Server error submitting set' })
            })
        }
    }, [selected, submitSelected, toasts])

    const onStart = async () => {
        try {
            const res = await start(username)
            toasts.add({ severity: 'success', message: `Welcome, ${res.name}! Game session started.` })
        } catch (e: any) {
            toasts.add({ severity: 'error', message: e?.message || 'Failed to start session' })
        }
    }

    useEffect(() => {
        if (!startAt) {
            setElapsed(0)
            return
        }
        let rafId: number | null = null
        let lastShown = -1
        const loop = () => {
            if (!startAt) return
            const secs = Math.max(0, Math.floor((Date.now() - startAt) / 1000))
            if (secs !== lastShown) {
                setElapsed(secs)
                lastShown = secs
            }
            if (!complete) rafId = requestAnimationFrame(loop)
        }
        loop()
        return () => { if (rafId != null) cancelAnimationFrame(rafId) }
    }, [startAt, complete])

    const mm = Math.floor(elapsed / 60).toString().padStart(2, '0')
    const ss = (elapsed % 60).toString().padStart(2, '0')

    return (
        <div className="container">
            <h1>Daily Set</h1>
            <div className="controls">
                {startAt ? (
                    <span id="timer" className="timer">{mm}:{ss}</span>
                ) : null}
            </div>

            {/* Landing overlay: shown when page first loads and no active session */}
            {!sessionId && !startAt && (
                <div className="overlay">
                    <div className="overlay-card" role="dialog" aria-labelledby="overlay-title">
                        <div id="overlay-title" className="overlay-title">
                            <span className="overlay-name">Daily Set</span>
                            <span className="overlay-date">{todayLabel}</span>
                        </div>
                        {completedToday ? (
                            <div className="completed-summary">
                                <p className="overlay-hint">You’ve already completed today’s game. Come back tomorrow!</p>
                                <div className="completed-stats">
                                    <div>
                                        <strong>Your time:</strong> {formatSeconds(completedDetail?.seconds)}
                                    </div>
                                    <div>
                                        <strong>Placement:</strong>{' '}
                                        {completedDetail?.placement != null ? `#${completedDetail.placement}` : '—'}
                                    </div>
                                    <div>
                                        <strong>Completed at:</strong>{' '}
                                        {completedDetail?.completed_at ? new Date(completedDetail.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                                    </div>
                                </div>

                                {/* Set previews removed for now */}

                                <div className="overlay-leaderboard">
                                    <Leaderboard limit={10} />
                                </div>
                            </div>
                        ) : (
                            <>
                                <div className="overlay-row">
                                    <input
                                        className="overlay-input"
                                        placeholder="Enter name (optional)"
                                        value={username}
                                        maxLength={12}
                                        onChange={(e) => {
                                            const raw = e.target.value
                                            // Allow only letters, numbers, underscore, hyphen; truncate to 12
                                            const sanitized = raw.replace(/[^A-Za-z0-9_-]/g, '').slice(0, 12)
                                            setUsername(sanitized)
                                        }}
                                        onKeyDown={(e) => { if (e.key === 'Enter') onStart() }}
                                        autoFocus
                                    />
                                    <button className="overlay-btn" onClick={onStart}>Start Game</button>
                                </div>
                                <p className="overlay-hint">Your game will resume if you reload this page.</p>
                            </>
                        )}
                    </div>
                </div>
            )}

            {loading && (
                <div id="board" className="board">
                    {SKELETON_KEYS.map((k) => (
                        <div key={k} className="card skeleton">
                            <div className="skeleton-content">
                                <div className="skeleton-symbols">
                                    <div className="skeleton-symbol" />
                                    <div className="skeleton-symbol" />
                                    <div className="skeleton-symbol" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {!loading && !error && board && startAt && !complete && (
                <Board
                    board={board}
                    selected={selected}
                    onSelect={toggleSelect}
                    cleared={cleared}
                    preStart={!startAt}
                    gameOver={complete}
                />
            )}

            {error && <div className="error">Error: {error}</div>}

            {complete && (
                <div className="gameover">
                    <div><strong>All sets found.</strong> Nice work!</div>
                    {foundSets?.length ? (
                        <>
                            <div className="found-title">Sets found ({foundSets.length}):</div>
                            <FoundSetsGallery sets={foundSets} />
                        </>
                    ) : null}
                </div>
            )}
        </div>
    )
}

export default function App() {
    const [lbOpen, setLbOpen] = useState(false)
    return (
        <ToastProvider>
            <MenuTab onOpenLeaderboard={() => setLbOpen((v) => !v)} />
            <LeaderboardPanel open={lbOpen} onClose={() => setLbOpen(false)} />
            <InnerApp />
        </ToastProvider>
    )
}
