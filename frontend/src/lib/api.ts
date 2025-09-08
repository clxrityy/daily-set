export type Card = [number, number, number, number]

export type SubmitSetPayload = {
    username?: string | null
    indices: number[]
    date?: string | null
    seconds?: number | null
    session_id?: string | null
    session_token?: string | null
}

export type SubmitResultOk = { ok: true; data: any }
export type SubmitResultErr = { ok: false; data: any; userFriendly?: boolean }
export type SubmitResult = SubmitResultOk | SubmitResultErr
export type Leader = { username: string; best: number; completed_at?: string | null }
export type LeaderboardResponse = { date: string; leaders: Leader[] }
export type FoundSetsResponse = { username: string; date: string; sets: Card[][] }

export async function enhancedFetch(url: string, options: RequestInit & { timeout?: number } = {}) {
    const { timeout = 10000, ...fetchOptions } = options
    const controller = new AbortController()
    const id = setTimeout(() => controller.abort(), timeout)
    try {
        const res = await fetch(url, { ...fetchOptions, signal: controller.signal })
        clearTimeout(id)
        if (!res.ok) {
            const errorData: any = { status: res.status, statusText: res.statusText, url: res.url }
            try {
                const data: any = await res.json()
                errorData.detail = data?.detail || data?.message
                errorData.data = data
            } catch {
                errorData.detail = res.statusText
            }
            throw errorData
        }
        return res
    } catch (err: any) {
        clearTimeout(id)
        if (err?.name === 'AbortError') {
            const e = new Error('Request timeout') as any
            e.name = 'TimeoutError'
            e.status = 408
            throw e
        }
        throw err
    }
}

export async function loadDaily(): Promise<Card[]> {
    const res = await enhancedFetch('/api/daily')
    const data = await res.json()
    return data.board as Card[]
}

export async function loadLeaderboard(params?: { date?: string; limit?: number }): Promise<LeaderboardResponse> {
    const date = params?.date?.trim()
    const limit = params?.limit
    const qs = new URLSearchParams()
    if (date) qs.set('date', date)
    if (typeof limit === 'number') qs.set('limit', String(limit))
    const url = qs.toString() ? `/api/leaderboard?${qs.toString()}` : '/api/leaderboard'
    const res = await enhancedFetch(url)
    return res.json()
}

export async function loadFoundSets(params: { username: string; date?: string }): Promise<FoundSetsResponse> {
    const qs = new URLSearchParams()
    qs.set('username', params.username)
    if (params.date?.trim()) qs.set('date', params.date.trim())
    const url = `/api/found_sets?${qs.toString()}`
    const res = await enhancedFetch(url)
    return res.json()
}

export async function startSession(username: string) {
    const res = await enhancedFetch('/api/start_session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
    })
    return res.json()
}

export async function loadStatus(): Promise<{ date: string; completed: boolean; seconds?: number; completed_at?: string | null; placement?: number }> {
    const res = await enhancedFetch('/api/status')
    return res.json()
}

export async function loadActiveSession(): Promise<{ active: boolean; session_id?: string; start_ts?: string | null; board?: Card[] }> {
    const res = await enhancedFetch('/api/session')
    return res.json()
}

export async function submitSet(payload: SubmitSetPayload): Promise<SubmitResult> {
    try {
        const res = await enhancedFetch('/api/submit_set', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        return { ok: true as const, data: await res.json() }
    } catch (error: any) {
        if (error?.status === 400 && error.detail) {
            return { ok: false as const, data: { detail: error.detail }, userFriendly: true }
        }
        return { ok: false as const, data: error }
    }
}
