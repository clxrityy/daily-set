import React, { useCallback, useEffect, useRef, useState } from 'react'
import type { Leader, LeaderboardResponse, FoundSetsResponse } from '../lib/api'
import { loadLeaderboard, loadFoundSets } from '../lib/api'
import { FoundSetsGallery } from './FoundSetsGallery'

export function Leaderboard({ date, limit = 8 }: { readonly date?: string; readonly limit?: number }) {
    const [data, setData] = useState<LeaderboardResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const refetchTimer = useRef<number | null>(null)
    const wsRetryTimer = useRef<number | null>(null)
    const [selectedUser, setSelectedUser] = useState<string | null>(null)
    const [userSets, setUserSets] = useState<FoundSetsResponse | null>(null)
    const [userSetsError, setUserSetsError] = useState<string | null>(null)
    const [userSetsLoading, setUserSetsLoading] = useState(false)

    const fetchNow = useCallback(() => {
        let cancelled = false
        setLoading(true)
        setError(null)
        loadLeaderboard({ date, limit })
            .then((d) => { if (!cancelled) setData(d) })
            .catch((e) => { if (!cancelled) setError(e?.detail || e?.message || 'Failed to load leaderboard') })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [date, limit])

    useEffect(() => {
        const cancel = fetchNow()
        return () => { cancel() }
    }, [fetchNow])

    useEffect(() => {
        let alive = true
        let ws: WebSocket | null = null
        let retryDelay = 800
        const scheduleRefetch = () => {
            if (refetchTimer.current != null) return
            refetchTimer.current = window.setTimeout(() => {
                refetchTimer.current = null
                fetchNow()
            }, 300) as unknown as number
        }
        const usingGateway = Boolean((import.meta as any)?.env?.VITE_REALTIME_WS_URL)
        const getWsUrl = () => {
            const envUrl = (import.meta as any)?.env?.VITE_REALTIME_WS_URL as string | undefined
            if (envUrl?.startsWith('ws')) return envUrl
            const { protocol, host } = window.location
            const wsProto = protocol === 'https:' ? 'wss' : 'ws'
            return `${wsProto}://${host}/ws`
        }
        const roomForDate = (d?: string | null) => {
            if (!d) return null
            return `daily-${String(d).replace(/-/g, '')}`
        }
        const connect = () => {
            try {
                ws = new WebSocket(getWsUrl())
            } catch {
                // schedule retry
                if (!alive) return
                wsRetryTimer.current = window.setTimeout(connect, retryDelay) as unknown as number
                retryDelay = Math.min(5000, Math.floor(retryDelay * 1.5))
                return
            }
            ws.onopen = () => {
                retryDelay = 800
                if (usingGateway) {
                    const room = roomForDate(date)
                    if (room) {
                        try { ws?.send(JSON.stringify({ v: 1, type: 'subscribe', room })) } catch { /* noop */ }
                    }
                }
            }
            ws.onmessage = (ev) => {
                try {
                    const msg = JSON.parse(ev.data)
                    if (!msg) return
                    // Support both direct events (Python WS) and broker envelopes (Go gateway)
                    const t = msg.type
                    const payloadEvent = msg?.payload?.event
                    const it = payloadEvent?.type
                    if (t === 'leaderboard_change' || t === 'completion' || it === 'leaderboard_change' || it === 'completion') {
                        // If a specific date is requested, only refetch when it matches
                        const msgDate = msg.date || payloadEvent?.date
                        if (!date || msgDate === date) scheduleRefetch()
                    }
                } catch { /* ignore */ }
            }
            ws.onerror = () => { try { ws?.close() } catch { /* noop */ } }
            ws.onclose = () => {
                if (!alive) return
                wsRetryTimer.current = window.setTimeout(connect, retryDelay) as unknown as number
                retryDelay = Math.min(5000, Math.floor(retryDelay * 1.5))
            }
        }
        connect()
        return () => {
            alive = false
            if (ws) { try { ws.close() } catch { /* noop */ } }
            if (wsRetryTimer.current != null) { clearTimeout(wsRetryTimer.current); wsRetryTimer.current = null }
            if (refetchTimer.current != null) { clearTimeout(refetchTimer.current); refetchTimer.current = null }
        }
    }, [date, fetchNow])

    if (loading) {
        return (
            <div className="leaderboard" aria-busy="true" aria-live="polite">
                <h2>Leaderboard — {date ?? ''}</h2>
                <div className="lb-wrap">
                    <table className="lb-table" role="table" aria-hidden="true">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Player</th>
                                <th>Best</th>
                                <th className="col-completed">Completed at</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Array.from({ length: 2 }).map((_, i) => (
                                <tr key={`skel-row-${(i + 1).toString(36)}`} className="lb-skel-row">
                                    <td><div className="sk sk-num" /></td>
                                    <td><div className="sk sk-name" /></td>
                                    <td><div className="sk sk-time" /></td>
                                    <td className="col-completed"><div className="sk sk-time" /></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        )
    }
    if (error) return <div className="leaderboard error">{error}</div>
    if (!data) return null

    const leaders: Leader[] = data.leaders || []

    // Helper: format seconds as mm:ss
    const fmt = (secs: number) => {
        const m = Math.floor(secs / 60).toString().padStart(2, '0')
        const s = (secs % 60).toString().padStart(2, '0')
        return `${m}:${s}`
    }
    // Detect ties on whole seconds
    const counts = new Map<number, number>()
    for (const l of leaders) counts.set(l.best, (counts.get(l.best) || 0) + 1)

    const fmtClock = (iso?: string | null) => {
        if (!iso) return '—'
        // Defensive parsing: if the string lacks timezone info, assume UTC
        const hasTZ = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso)
        const dt = new Date(hasTZ ? iso : iso + 'Z')
        const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
        const local = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', timeZone }).format(dt)
        // Extract short TZ label in a locale-safe way
        const tzParts = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', timeZoneName: 'short', timeZone }).formatToParts(dt)
        const tz = tzParts.find(p => p.type === 'timeZoneName')?.value || timeZone
        const uh = String(dt.getUTCHours()).padStart(2, '0')
        const um = String(dt.getUTCMinutes()).padStart(2, '0')
        const utc = `${uh}:${um} UTC`
        return (
            <span title={`UTC: ${utc}`}>
                {local} <span className="tz">{tz}</span>
            </span>
        )
    }

    const onClickUser = async (uname: string) => {
        setSelectedUser(uname)
        setUserSets(null)
        setUserSetsError(null)
        setUserSetsLoading(true)
        try {
            const res = await loadFoundSets({ username: uname, date: data.date })
            setUserSets(res)
        } catch (e: any) {
            setUserSetsError(e?.detail || e?.message || 'Failed to load sets')
        } finally {
            setUserSetsLoading(false)
        }
    }

    return (
        <div className="leaderboard" aria-live="polite" {...(loading ? { 'aria-busy': 'true' } : {})}>
            <h2>Leaderboard — {data.date}</h2>
            {leaders.length === 0 ? (
                <div>No entries yet. Be the first!</div>
            ) : (
                <div className="lb-wrap">
                    <table className="lb-table" role="table">
                        <thead>
                            <tr>
                                <th scope="col">#</th>
                                <th scope="col">Player</th>
                                <th scope="col">Best</th>
                                <th scope="col" className="col-completed">Completed at</th>
                            </tr>
                        </thead>
                        <tbody>
                            {leaders.map((l, i) => {
                                const tie = (counts.get(l.best) || 0) > 1
                                return (
                                    <tr key={`${l.username}-${i}`} onClick={() => onClickUser(l.username)}>
                                        <td>{i + 1}</td>
                                        <td>
                                            <button
                                                type="button"
                                                className="lb-user"
                                                onClick={() => onClickUser(l.username)}
                                                aria-label={`View sets found by ${l.username}`}
                                            >
                                                {l.username}
                                            </button>
                                        </td>
                                        <td>
                                            {fmt(l.best)} {tie && <span className="tie-badge" title="Same second as another score">tie</span>}
                                        </td>
                                        <td className="col-completed">{fmtClock(l.completed_at)}</td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                    {selectedUser && (
                        <div className="user-sets-panel" role="region" aria-live="polite" aria-label={`Sets found by ${selectedUser}`}>
                            <div className="user-sets-header">
                                <strong>{selectedUser}</strong>
                                <button className="user-sets-close" onClick={() => { setSelectedUser(null); setUserSets(null) }} aria-label="Close">
                                    ×
                                </button>
                            </div>
                            {userSetsLoading && <div className="user-sets-loading">Loading sets…</div>}
                            {userSetsError && <div className="user-sets-error">{userSetsError}</div>}
                            {!!userSets?.sets?.length && (
                                <FoundSetsGallery sets={userSets.sets} />
                            )}
                            {userSets && !userSets.sets?.length && !userSetsLoading && !userSetsError && (
                                <div className="user-sets-empty">No sets recorded.</div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
