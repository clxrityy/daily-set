import React from 'react'
import type { Card } from '../lib/api'
// eslint-disable-next-line @typescript-eslint/consistent-type-imports
import { CardView } from './Card'

export function Board({ board, selected, onSelect, cleared, preStart, gameOver }:
    { readonly board: Card[], readonly selected?: ReadonlyArray<number>, readonly onSelect?: (idx: number) => void, readonly cleared?: ReadonlySet<number>, readonly preStart?: boolean, readonly gameOver?: boolean }) {
    const selSet = new Set(selected ?? [])
    return (
        <div className="board-container">
            <div id="board" className={`board${preStart ? ' prestart' : ''}${gameOver ? ' gameover' : ''} board`}>
                {board.map((c, i) => (
                    <CardView
                        key={`${i}-${c.join('-')}`}
                        card={c}
                        idx={i}
                        selected={selSet.has(i)}
                        onSelect={preStart || gameOver ? undefined : onSelect}
                        cleared={cleared?.has(i)}
                    />
                ))}
            </div>
        </div>
    )
}
