import { useCallback, useEffect, useMemo, useState } from 'react'
import { loadDaily, startSession as apiStart, submitSet } from './api'
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
    const adj = adjectives[Math.floor(Math.random() * adjectives.length)]
    const noun = nouns[Math.floor(Math.random() * nouns.length)]
    const num = Math.floor(Math.random() * 100)
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
            if (Array.isArray(saved.board) && saved.board.length) setBoard(saved.board)
            else setBoard(await loadDaily())
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

    const load = useCallback(async () => {
        const restored = await restoreFromStorage()
        if (restored) return
        const b = await loadDaily()
        setBoard(b)
        setSelected([])
        setCleared(new Set())
    }, [restoreFromStorage])

    const start = useCallback(async (username?: string | null) => {
        const raw = (username ?? '').trim()
        const safe = raw.replace(/[^A-Za-z0-9_-]/g, '').slice(0, 12)
        const name = safe || randomUsername()
        const res = await apiStart(name)
        setSessionId(res.session_id ?? null)
        setSessionToken(res.session_token ?? null)
        const now = Date.now()
        setStartAt(now)
        // Persist immediately with current board snapshot
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                date: today(),
                startAt: now,
                board,
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

    const submitSelected = useCallback(async (): Promise<SubmitResult | { ok: false; reason: 'need-3' }> => {
        if (selected.length !== 3) return { ok: false as const, reason: 'need-3' }
        // Client-side validation to avoid false 400s due to index drift
        const [i, j, k] = selected as [number, number, number]
        const a = board[i]
        const b = board[j]
        const c = board[k]
        if (!a || !b || !c || !isValidSet(a, b, c)) {
            return { ok: false as const, data: { detail: 'Not a set (client check)' }, userFriendly: true } as SubmitResult
        }
        const secs = startAt ? Math.floor((Date.now() - startAt) / 1000) : null
        const res = await submitSet({
            indices: selected,
            seconds: secs,
            session_id: sessionId,
            session_token: sessionToken,
        })
        // Hint for users if session wasn't started
        if (!res.ok && !sessionId) {
            (res as any).userFriendly = true
                ; (res as any).data = { detail: 'Tip: click Start Game to keep server and client boards in sync.' }
        }
        if (res.ok) {
            // Capture the found set for later display
            if (a && b && c) {
                setFoundSets((prev) => [...prev, [a, b, c]])
            }
            const sorted = [...selected].sort((a, b) => b - a)
            if (sessionId) {
                setBoard((b) => {
                    const copy = [...b]
                    for (const idx of sorted) copy.splice(idx, 1)
                    return copy
                })
            } else {
                // No session: flip these cards to a "cleared" back state
                setCleared((prev) => new Set([...prev, ...selected]))
            }
            setSelected([])
        }
        return res
    }, [selected, startAt, sessionId, sessionToken, board])

    const complete = useMemo(() => !hasValidSets(board, cleared), [board, cleared])

    // Persist session state whenever it changes (and a session exists)
    useEffect(() => {
        if (!sessionId) return
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
        if (complete) {
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
    }, [complete, foundSets])

    return { board, setBoard, load, selected, setSelected, toggleSelect, submitSelected, start, startAt, complete, cleared, sessionId }
}
