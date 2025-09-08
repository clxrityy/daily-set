import React, { useEffect, useRef } from 'react'
import type { Card } from '../lib/api'
import { createSymbolSVG } from '../lib/svg'

function MiniCard({ card }: { readonly card: Card }) {
    const [shape, colorIdx, shading, count] = card
    const symbolsRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        let canceled = false
        const el = symbolsRef.current
        if (!el) return
        el.innerHTML = ''
        for (let n = 0; n < count; n++) {
            if (canceled) return
            const svg = createSymbolSVG(shape, colorIdx, shading)
            svg.setAttribute('aria-hidden', 'true')
            el.appendChild(svg)
        }
        return () => { canceled = true }
    }, [shape, colorIdx, shading, count])

    return (
        <div className="mini-card" aria-hidden>
            <div className="symbols" ref={symbolsRef} />
        </div>
    )
}

export function FoundSetsGallery({ sets }: { readonly sets: ReadonlyArray<readonly Card[]> }) {
    if (!sets?.length) return null
    return (
        <div className="found-gallery" role="list" aria-label="Sets you found">
            {sets.map((triplet) => {
                const key = JSON.stringify(triplet)
                if (!triplet || triplet.length !== 3) return null
                const [c0, c1, c2] = triplet as readonly [Card, Card, Card]
                return (
                    <div key={key} className="set-row" role="listitem" aria-label="Set of three cards">
                        <MiniCard card={c0} />
                        <MiniCard card={c1} />
                        <MiniCard card={c2} />
                    </div>
                )
            })}
        </div>
    )
}

export default FoundSetsGallery
