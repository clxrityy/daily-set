import React, { useEffect, useRef } from 'react'
import type { Card as CardTuple } from '../lib/api'
import { createSymbolSVG } from '../lib/svg'

// We will reuse the existing svg.js createSymbolSVG via dynamic import and DOM append
export function CardView({ card, idx, selected, onSelect, cleared, preStart }: {
    readonly card: CardTuple,
    readonly idx: number,
    readonly selected?: boolean,
    readonly onSelect?: (idx: number) => void,
    readonly cleared?: boolean,
    readonly preStart?: boolean
}) {
    const [shape, colorIdx, shading, count] = card
    const symbolsRef = useRef<HTMLDivElement>(null)
    const containerRef = useRef<HTMLDivElement>(null)
    const isSel = !!selected

    useEffect(() => {
        let canceled = false
        function render() {
            if (!symbolsRef.current) return
            symbolsRef.current.innerHTML = ''
            for (let n = 0; n < count; n++) {
                if (canceled) return
                const svg = createSymbolSVG(shape, colorIdx, shading)
                svg.classList.add('symbol')
                symbolsRef.current.appendChild(svg)
            }
        }
        render()
        return () => { canceled = true }
    }, [shape, colorIdx, shading, count])

    useEffect(() => {
        const el = containerRef.current
        if (!el) return
        el.setAttribute('aria-pressed', isSel ? 'true' : 'false')
    }, [isSel])

    const isCleared = !!cleared
    const isPreStart = !!preStart
    return (
        <div
            ref={containerRef}
            className={`card${isSel ? ' sel' : ''}${isCleared ? ' cleared' : ''}${isPreStart ? ' prestart' : ''}`}
            data-index={idx}
            role="button"
            tabIndex={0}
            aria-label={`Card ${idx + 1}`}
            onClick={(e) => {
                if (isCleared || isPreStart) return
                const wasSelected = isSel
                onSelect?.(idx)
                // If this was a mouse-initiated deselection, blur to remove focus ring
                // e.detail !== 0 indicates a pointer/mouse click; keyboard-initiated clicks have detail === 0
                if (wasSelected && (e as React.MouseEvent).detail !== 0) {
                    (e.currentTarget as HTMLElement).blur()
                }
            }}
            onKeyDown={(ev) => {
                if (isCleared || isPreStart) return
                if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault(); onSelect?.(idx)
                    return
                }
                if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft' || ev.key === 'ArrowUp' || ev.key === 'ArrowDown') {
                    const maybeBoard = ev.currentTarget.closest('#board')
                    if (!(maybeBoard instanceof HTMLElement)) return
                    const board = maybeBoard
                    const cards = Array.from(board.querySelectorAll<HTMLElement>('.card'))
                    const curIndex = cards.indexOf(ev.currentTarget as HTMLElement)
                    if (curIndex === -1) return
                    const cols = Math.max(1, Math.round(board.clientWidth / Math.max(1, (ev.currentTarget as HTMLElement).clientWidth)))
                    let next = curIndex
                    if (ev.key === 'ArrowRight') next = (curIndex + 1) % cards.length
                    if (ev.key === 'ArrowLeft') next = (curIndex - 1 + cards.length) % cards.length
                    if (ev.key === 'ArrowDown') next = Math.min(cards.length - 1, curIndex + cols)
                    if (ev.key === 'ArrowUp') next = Math.max(0, curIndex - cols)
                    cards[next]?.focus()
                }
            }}
        >
            <div className="symbols" ref={symbolsRef} />
        </div>
    )
}
