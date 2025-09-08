import React, { useEffect, useState } from 'react'
import { Leaderboard } from './Leaderboard'

type TabKey = 'daily' | 'weekly' | 'monthly'

export function LeaderboardPanel({ open, onClose }: { readonly open: boolean; readonly onClose: () => void }) {
    const [tab, setTab] = useState<TabKey>('daily')
    useEffect(() => {
        if (!open) return
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose()
        }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [open, onClose])

    if (!open) return null

    return (
        <>
            <div className="side-backdrop" aria-hidden onClick={onClose} />
            <aside className="side-panel" aria-label="Leaderboard panel">
                <div className="side-header">
                    <h2>Leaderboard</h2>
                </div>
                <div className="side-tabs" role="group" aria-label="Leaderboard views">
                    <button type='button' className={`side-tab${tab === 'daily' ? ' active' : ''}`} onClick={() => setTab('daily')}>Daily</button>
                    <button type='button' className={`side-tab${tab === 'weekly' ? ' active' : ''}`} onClick={() => setTab('weekly')}>Weekly</button>
                    <button type='button' className={`side-tab${tab === 'monthly' ? ' active' : ''}`} onClick={() => setTab('monthly')}>Monthly</button>
                </div>
                <div className="side-body">
                    {tab === 'daily' && <Leaderboard limit={25} />}
                    {tab === 'weekly' && <div className="coming-soon">Weekly leaderboard coming soon…</div>}
                    {tab === 'monthly' && <div className="coming-soon">Monthly leaderboard coming soon…</div>}
                </div>
            </aside>
        </>
    )
}
