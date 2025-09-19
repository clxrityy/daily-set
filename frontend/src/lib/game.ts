import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { startSession as apiStart, submitSet, loadActiveSession } from './api'
import type { Card, SubmitResult } from './api'

export function isValidSet(a: Card, b: Card, c: Card) {
    for (let i = 0; i < 4; i++) {
        const vals = new Set([a[i], b[i], c[i]])
        if (vals.size === 2) return false
    }
    return true
}

// Helper function to check if a triplet forms a valid set
function checkTriplet(board: ReadonlyArray<Card>, i: number | undefined, j: number | undefined, k: number | undefined): boolean {
    return i !== undefined && j !== undefined && k !== undefined &&
        isValidSet(board[i] as Card, board[j] as Card, board[k] as Card);
}

// Helper function to check if any valid set exists in the given indices
function checkForValidSets(board: ReadonlyArray<Card>, indices: number[]): boolean {
    for (let i = 0; i < indices.length - 2; i++) {
        const idxI = indices[i]
        for (let j = i + 1; j < indices.length - 1; j++) {
            const idxJ = indices[j]
            for (let k = j + 1; k < indices.length; k++) {
                const idxK = indices[k]
                if (checkTriplet(board, idxI, idxJ, idxK)) return true
            }
        }
    }
    return false
}

export function hasValidSets(board: ReadonlyArray<Card>, cleared?: ReadonlySet<number>) {
    if (board.length < 3) return false

    // Filter out cleared cards
    const validIndices = []
    for (let i = 0; i < board.length; i++) {
        if (!(cleared?.has(i))) {
            validIndices.push(i)
        }
    }

    // Need at least 3 cards to form a set
    if (validIndices.length < 3) return false

    // Check for valid sets using the helper function
    return checkForValidSets(board, validIndices)
}

function randomUsername() {
    const adjectives = ["Swift", "Quick", "Clever", "Sharp", "Bright", "Smart", "Fast", "Keen", "Wise", "Bold"]
    const nouns = ["Ace", "Pro", "Star", "Bee", "Hawk", "Wolf", "Lynx", "Fox", "Owl", "Bear"]
    const adjIdxArr = new Uint32Array(1); window.crypto.getRandomValues(adjIdxArr); const adj = adjectives[adjIdxArr[0] % adjectives.length];
    const nounIdxArr = new Uint32Array(1); window.crypto.getRandomValues(nounIdxArr); const noun = nouns[nounIdxArr[0] % nouns.length];
    const numArr = new Uint32Array(1); window.crypto.getRandomValues(numArr); const num = numArr[0] % 100;
    const base = `${adj}${noun}${num}`.replace(/[^A-Za-z0-9_-]/g, '')
    return base.slice(0, 12)
}

export function useGame() {
    const [board, setBoard] = useState<Card[]>([])
    const [selected, setSelected] = useState<number[]>([])
    const [cleared, setCleared] = useState<Set<number>>(new Set())
    const [startAt, setStartAt] = useState<number | null>(null)
    const [sessionId, setSessionId] = useState<string | null>(null)
    const [sessionToken, setSessionToken] = useState<string | null>(null)
    const STORAGE_KEY = 'ds_session_v1'
    const COMPLETED_KEY = 'ds_completed_v1'
    const [foundSets, setFoundSets] = useState<Card[][]>([])

    const today = () => new Date().toISOString().slice(0, 10)

    const restoreFromStorage = useCallback(async (): Promise<boolean> => {
        try {
            const raw = localStorage.getItem(STORAGE_KEY)
            if (!raw) return false
            const saved = JSON.parse(raw)
            if (saved?.date !== today()) {
                localStorage.removeItem(STORAGE_KEY)
                return false
            }
            // Only restore board if a game session was started
            if (typeof saved.startAt === 'number' && Array.isArray(saved.board) && saved.board.length) {
                setBoard(saved.board)
            } else {
                return false
            }
            setSelected([])
            setCleared(new Set(Array.isArray(saved.cleared) ? saved.cleared : []))
            setSessionId(saved.sessionId || null)
            setSessionToken(saved.sessionToken || null)
            setStartAt(typeof saved.startAt === 'number' ? saved.startAt : null)
            if (Array.isArray(saved.foundSets)) setFoundSets(saved.foundSets)
            return true
        } catch {
            return false
        }
    }, [])

    // Helper function to get saved start time from local storage
    const getSavedStartTime = useCallback((): number | null => {
        try {
            const raw = localStorage.getItem(STORAGE_KEY)
            if (!raw) return null

            const saved = JSON.parse(raw)
            if (saved?.date === today() && typeof saved.startAt === 'number') {
                return saved.startAt
            }
        } catch { /* noop */ }
        return null
    }, [])

    // Helper function to persist session data to local storage
    const persistSessionData = useCallback((board: Card[], effectiveStart: number | null, sessionId: string | null) => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                date: today(),
                startAt: effectiveStart,
                board,
                cleared: [],
                sessionId: sessionId || null,
                sessionToken,
                foundSets,
            }))
        } catch { /* noop */ }
    }, [sessionToken, foundSets])

    // Helper function to load and process server-side session
    // Debounce state to avoid spamming /api/session across rapid re-renders
    const pendingLoadRef = useRef<Promise<any> | null>(null)
    const lastLoadTsRef = useRef<number>(0)

    const loadServerSession = useCallback(async (savedStartAt: number | null): Promise<boolean> => {
        try {
            const nowTs = Date.now()
            if (pendingLoadRef.current) {
                // Reuse the in-flight request
                const s = await pendingLoadRef.current
                return !!(s?.active && Array.isArray(s.board))
            }
            if (nowTs - lastLoadTsRef.current < 200) {
                // Too soon since last successful call; skip
                return false
            }
            const p = loadActiveSession()
            pendingLoadRef.current = p
            const s = await p
            pendingLoadRef.current = null
            lastLoadTsRef.current = Date.now()
            if (!s?.active || !s.board || !Array.isArray(s.board)) return false;

            setBoard(s.board)
            setSessionId(s.session_id || null)

            const parsed = s.start_ts ? Date.parse(s.start_ts) : NaN
            const now = Date.now()
            let effectiveStart: number | null = Number.isFinite(parsed) ? parsed : savedStartAt
            // Guard: if server-start is in the future relative to client clock (>3s), fall back
            if (typeof effectiveStart === 'number' && effectiveStart - now > 3000) {
                effectiveStart = savedStartAt ?? now
            }
            if (!(typeof effectiveStart === 'number' && effectiveStart)) {
                // As a last resort, start now so the timer ticks
                effectiveStart = Date.now()
            }
            setStartAt(effectiveStart)
            setCleared(new Set())

            persistSessionData(s.board, effectiveStart, s.session_id || null)
            return true
        } catch { /* ignore */ pendingLoadRef.current = null }
        return false
    }, [persistSessionData])

    const load = useCallback(async (): Promise<boolean> => {
        // Read any locally persisted session snapshot upfront (for fallback start time)
        const savedStartAt = getSavedStartTime()

        // 1) Prefer server-side active session (authoritative)
        if (await loadServerSession(savedStartAt)) {
            return true
        }

        // 2) Fall back to localStorage restore (only if started previously)
        if (await restoreFromStorage()) {
            return true
        }

        // 3) Not started: do not fetch the board yet
        return false
    }, [getSavedStartTime, loadServerSession, restoreFromStorage])

    const start = useCallback(async (username?: string | null) => {
        const raw = (username ?? '').trim()
        const safe = raw.replace(/[^A-Za-z0-9_-]/g, '').slice(0, 12)
        const name = safe || randomUsername()
        const res = await apiStart(name)
        // Persist last used username for future prefill
        try {
            localStorage.setItem('ds_last_username', name)
        } catch { /* ignore */ }
        setSessionId(res.session_id ?? null)
        setSessionToken(res.session_token ?? null)
        const parsedServerStart = res?.start_ts ? Date.parse(res.start_ts) : NaN
        const now = Date.now()
        let effectiveStart = Number.isFinite(parsedServerStart) ? parsedServerStart : now
        // Guard: if server-start is ahead of client clock (>3s), use client now
        if (effectiveStart - now > 3000) {
            effectiveStart = now
        }
        setStartAt(effectiveStart)
        // Load the authoritative daily board after session start
        let newBoard: Card[] | null = null
        try {
            const resp = await fetch('/api/daily', { credentials: 'same-origin' })
            const data = await resp.json()
            if (Array.isArray(data?.board)) {
                newBoard = data.board as Card[]
                setBoard(newBoard)
            }
        } catch { /* ignore network error */ }
        // Persist immediately with current board snapshot
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                date: today(),
                startAt: effectiveStart,
                board: newBoard ?? board,
                cleared: Array.from(cleared),
                sessionId: res.session_id ?? null,
                sessionToken: res.session_token ?? null,
                username: name,
                foundSets,
            }))
        } catch { /* noop */ }
        return { name, ...res }
    }, [])

    const toggleSelect = useCallback((idx: number) => {
        // Do not allow selecting already-cleared cards
        if (cleared.has(idx)) return
        setSelected((cur) => {
            const i = cur.indexOf(idx)
            if (i !== -1) return [...cur.slice(0, i), ...cur.slice(i + 1)]
            if (cur.length >= 3) return cur
            return [...cur, idx]
        })
    }, [cleared])

    // Helpers to keep submitSelected simple
    const computeSeconds = (startedAt: number | null): number | null => {
        if (typeof startedAt !== 'number') return null
        const delta = Math.floor((Date.now() - startedAt) / 1000)
        return Number.isFinite(delta) ? Math.max(0, delta) : null
    }

    const buildPayload = (
        indices: number[],
        sessionIdValue: string | null,
        sessionTokenValue: string | null,
        secs: number | null,
    ) => {
        const payload: any = { indices }
        if (sessionIdValue) {
            payload.session_id = sessionIdValue
            payload.session_token = sessionTokenValue
            if (secs !== null) payload.seconds = secs
        }
        return payload
    }

    const applySetState = (indices: number[], hasSession: boolean) => {
        const sorted = [...indices].sort((a, b) => b - a)
        if (hasSession) {
            setBoard((b) => {
                const copy = [...b]
                for (const idx of sorted) copy.splice(idx, 1)
                return copy
            })
        } else {
            setCleared((prev) => new Set([...prev, ...indices]))
        }
        setSelected([])
    }

    const submitSelected = useCallback(async (): Promise<SubmitResult | { ok: false; reason: 'need-3' }> => {
        if (selected.length !== 3) return { ok: false as const, reason: 'need-3' }
        const [i, j, k] = selected as [number, number, number]
        const a = board[i]
        const b = board[j]
        const c = board[k]
        // Client-side validation
        const valid = !!a && !!b && !!c && isValidSet(a, b, c)
        if (!valid) {
            return { ok: false as const, data: { detail: 'Not a set (client check)' }, userFriendly: true } as SubmitResult
        }
        const secs = computeSeconds(startAt)
        const payload = buildPayload(selected, sessionId, sessionToken, secs)
        const res = await submitSet(payload)
        if (!res.ok && !sessionId) {
            (res as any).userFriendly = true
                ; (res as any).data = { detail: 'Tip: click Start Game to keep server and client boards in sync.' }
        }
        if (res.ok) {
            setFoundSets((prev) => [...prev, [a, b, c]])
            applySetState(selected, !!sessionId)
        }
        return res
    }, [selected, startAt, sessionId, sessionToken, board])

    const complete = useMemo(() => {
        // Only consider completion when a session has started and a board is present
        if (!startAt) return false
        if (!board || board.length < 3) return false
        return !hasValidSets(board, cleared)
    }, [board, cleared, startAt])

    // Persist session state whenever it changes (even without a server session)
    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                date: today(),
                startAt,
                board,
                cleared: Array.from(cleared),
                sessionId,
                sessionToken,
                foundSets,
            }))
        } catch { /* noop */ }
    }, [board, cleared, sessionId, sessionToken, startAt, foundSets])

    // If the game is complete, clear persisted session so next day starts clean
    useEffect(() => {
        if (complete && startAt && board && board.length >= 3) {
            try {
                // Persist a completion snapshot for overlay (keep for the day)
                localStorage.setItem(COMPLETED_KEY, JSON.stringify({
                    date: today(),
                    foundSets,
                }))
                // Clear active session state
                localStorage.removeItem(STORAGE_KEY)
            } catch { /* noop */ }
        }
    }, [complete, foundSets, startAt, board])

    return { board, setBoard, load, selected, setSelected, toggleSelect, submitSelected, start, startAt, complete, cleared, sessionId, foundSets }
}
