const SVG_NS = "http://www.w3.org/2000/svg" as const
const __svgPatternRegistry: Record<string, string> = {}

function ensureSharedDefs(): SVGDefsElement {
    let holder = document.getElementById("__svg_defs_holder") as SVGSVGElement | null
    if (!holder) {
        holder = document.createElementNS(SVG_NS, "svg")
        holder.setAttribute("id", "__svg_defs_holder")
        holder.style.position = "absolute"
        holder.style.width = "0"
        holder.style.height = "0"
        holder.style.overflow = "hidden"
        document.body.appendChild(holder)
    }
    let defs = holder.querySelector<SVGDefsElement>("defs")
    if (!defs) {
        defs = document.createElementNS(SVG_NS, "defs");
        holder.appendChild(defs)
    }
    return defs
}

function lightenColor(color: string, amount: number): string {
    const num = parseInt(color.replace("#", ""), 16)
    const amt = Math.round(255 * amount)
    const R = Math.min(255, (num >> 16) + amt)
    const G = Math.min(255, ((num >> 8) & 0x00ff) + amt)
    const B = Math.min(255, (num & 0x0000ff) + amt)
    return "#" + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)
}

function darkenColor(color: string, amount: number): string {
    const num = parseInt(color.replace("#", ""), 16)
    const amt = Math.round(255 * amount)
    const R = Math.max(0, (num >> 16) - amt)
    const G = Math.max(0, ((num >> 8) & 0x00ff) - amt)
    const B = Math.max(0, (num & 0x0000ff) - amt)
    return "#" + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)
}

function getOrCreateStripedPattern(color: string): string {
    const key = `stripe-${color}`
    if (__svgPatternRegistry[key]) return __svgPatternRegistry[key]
    const defs = ensureSharedDefs()
    const pattern = document.createElementNS(SVG_NS, "pattern")
    const id = `p-${Math.random().toString(36).slice(2, 8)}`
    pattern.setAttribute("id", id)
    pattern.setAttribute("patternUnits", "userSpaceOnUse")
    pattern.setAttribute("width", "6")
    pattern.setAttribute("height", "6")
    const path = document.createElementNS(SVG_NS, "path")
    path.setAttribute("d", "M0,6 L6,0")
    path.setAttribute("stroke", color)
    path.setAttribute("stroke-width", "3")
    pattern.appendChild(path)
    defs.appendChild(pattern)
    __svgPatternRegistry[key] = id
    return id
}

function getOrCreateSphereGradient(color: string): string {
    const key = `sphere-${color}`
    if (__svgPatternRegistry[key]) return __svgPatternRegistry[key]
    const defs = ensureSharedDefs()
    const gradient = document.createElementNS(SVG_NS, "radialGradient")
    const id = `g-${Math.random().toString(36).slice(2, 8)}`
    gradient.setAttribute("id", id)
    gradient.setAttribute("cx", "35%")
    gradient.setAttribute("cy", "35%")
    gradient.setAttribute("r", "65%")

    const stop1 = document.createElementNS(SVG_NS, "stop")
    stop1.setAttribute("offset", "0%")
    stop1.setAttribute("stop-color", lightenColor(color, 0.3))

    const stop2 = document.createElementNS(SVG_NS, "stop")
    stop2.setAttribute("offset", "70%")
    stop2.setAttribute("stop-color", color)

    const stop3 = document.createElementNS(SVG_NS, "stop")
    stop3.setAttribute("offset", "100%")
    stop3.setAttribute("stop-color", darkenColor(color, 0.2))

    gradient.appendChild(stop1)
    gradient.appendChild(stop2)
    gradient.appendChild(stop3)
    defs.appendChild(gradient)
    __svgPatternRegistry[key] = id
    return id
}

function getOrCreateDiamondGradients(color: string): { topId: string, bottomId: string } {
    const defs = ensureSharedDefs()
    const keyTop = `diamond-top-${color}`
    let topId = __svgPatternRegistry[keyTop]
    if (!topId) {
        const topGrad = document.createElementNS(SVG_NS, "linearGradient")
        topId = `dg-top-${Math.random().toString(36).slice(2, 8)}`
        topGrad.setAttribute("id", topId)
        topGrad.setAttribute("gradientUnits", "userSpaceOnUse")
        topGrad.setAttribute("x1", "50")
        topGrad.setAttribute("y1", "10")
        topGrad.setAttribute("x2", "50")
        topGrad.setAttribute("y2", "50")
        const s1 = document.createElementNS(SVG_NS, "stop")
        s1.setAttribute("offset", "0%")
        s1.setAttribute("stop-color", lightenColor(color, 0.35))
        const s2 = document.createElementNS(SVG_NS, "stop")
        s2.setAttribute("offset", "100%")
        s2.setAttribute("stop-color", darkenColor(color, 0.05))
        topGrad.appendChild(s1)
        topGrad.appendChild(s2)
        defs.appendChild(topGrad)
        __svgPatternRegistry[keyTop] = topId
    }

    const keyBottom = `diamond-bottom-${color}`
    let bottomId = __svgPatternRegistry[keyBottom]
    if (!bottomId) {
        const botGrad = document.createElementNS(SVG_NS, "linearGradient")
        bottomId = `dg-bot-${Math.random().toString(36).slice(2, 8)}`
        botGrad.setAttribute("id", bottomId)
        botGrad.setAttribute("gradientUnits", "userSpaceOnUse")
        botGrad.setAttribute("x1", "50")
        botGrad.setAttribute("y1", "50")
        botGrad.setAttribute("x2", "50")
        botGrad.setAttribute("y2", "90")
        const s1 = document.createElementNS(SVG_NS, "stop")
        s1.setAttribute("offset", "0%")
        s1.setAttribute("stop-color", lightenColor(color, 0.1))
        const s2 = document.createElementNS(SVG_NS, "stop")
        s2.setAttribute("offset", "100%")
        s2.setAttribute("stop-color", darkenColor(color, 0.25))
        botGrad.appendChild(s1)
        botGrad.appendChild(s2)
        defs.appendChild(botGrad)
        __svgPatternRegistry[keyBottom] = bottomId
    }

    return { topId, bottomId }
}

export function colorForIndex(i: number): string {
    const cols = ["#ef4444", "#10b981", "#7c3aed"]
    return cols[i % cols.length] || "#000"
}

// Helper functions to create shapes
function createCircleShape(): SVGCircleElement {
    const circle = document.createElementNS(SVG_NS, "circle")
    circle.setAttribute("cx", "50")
    circle.setAttribute("cy", "50")
    circle.setAttribute("r", "30")
    return circle
}

function createDiamondShape(color: string): {
    element: SVGGElement;
    topFacet: SVGPolygonElement;
    bottomFacet: SVGPolygonElement;
    glare: SVGPolygonElement;
    gradIds: { topId: string; bottomId: string }
} {
    const g = document.createElementNS(SVG_NS, "g")
    const topFacet = document.createElementNS(SVG_NS, "polygon")
    topFacet.setAttribute("points", "50,10 85,50 15,50")
    topFacet.setAttribute("fill", "none")

    const bottomFacet = document.createElementNS(SVG_NS, "polygon")
    bottomFacet.setAttribute("points", "15,50 85,50 50,90")
    bottomFacet.setAttribute("fill", "none")

    const glare = document.createElementNS(SVG_NS, "polygon")
    glare.setAttribute("points", "58,28 68,42 62,44 54,32")
    glare.setAttribute("fill", "none")
    glare.setAttribute("pointer-events", "none")

    g.appendChild(topFacet)
    g.appendChild(bottomFacet)
    g.appendChild(glare)

    const gradIds = getOrCreateDiamondGradients(color)

    return {
        element: g,
        topFacet,
        bottomFacet,
        glare,
        gradIds
    }
}

function createRectangularShape(): {
    element: SVGGElement;
    front: SVGRectElement;
    top: SVGPolygonElement;
    right: SVGPolygonElement
} {
    const g = document.createElementNS(SVG_NS, "g")

    const front = document.createElementNS(SVG_NS, "rect")
    front.setAttribute("x", "20")
    front.setAttribute("y", "25")
    front.setAttribute("width", "45")
    front.setAttribute("height", "45")
    front.setAttribute("stroke-width", "3")
    front.setAttribute("fill", "none")

    const top = document.createElementNS(SVG_NS, "polygon")
    top.setAttribute("points", "20,25 35,15 80,15 65,25")
    top.setAttribute("stroke-width", "3")
    top.setAttribute("fill", "none")

    const right = document.createElementNS(SVG_NS, "polygon")
    right.setAttribute("points", "65,25 80,15 80,60 65,70")
    right.setAttribute("stroke-width", "3")
    right.setAttribute("fill", "none")

    g.appendChild(front)
    g.appendChild(top)
    g.appendChild(right)

    return { element: g, front, top, right }
}

// Helper functions for shading
function applySolidShadingToCircle(circle: SVGElement, color: string, gradientId?: string): void {
    if (gradientId) circle.setAttribute("fill", `url(#${gradientId})`)
    circle.setAttribute("stroke", darkenColor(color, 0.1))
    circle.setAttribute("stroke-width", "2")
}

function applySolidShadingToDiamond(
    diamond: ReturnType<typeof createDiamondShape>,
    color: string
): void {
    const { topFacet, bottomFacet, glare, gradIds } = diamond

    if (gradIds.topId) topFacet.setAttribute("fill", `url(#${gradIds.topId})`)
    if (gradIds.bottomId) bottomFacet.setAttribute("fill", `url(#${gradIds.bottomId})`)

    for (const facet of [topFacet, bottomFacet]) {
        facet.setAttribute("stroke", darkenColor(color, 0.2))
        facet.setAttribute("stroke-width", "3")
        facet.setAttribute("stroke-linejoin", "round")
        facet.setAttribute("stroke-linecap", "round")
    }

    glare.setAttribute("fill", "#ffffff")
    glare.setAttribute("fill-opacity", "0.14")
    glare.setAttribute("stroke", "none")
}

function applySolidShadingToRectangle(
    rect: ReturnType<typeof createRectangularShape>,
    color: string
): void {
    const { front, top, right } = rect

    front.setAttribute("fill", color)
    front.setAttribute("stroke", darkenColor(color, 0.2))

    top.setAttribute("fill", lightenColor(color, 0.2))
    top.setAttribute("stroke", darkenColor(color, 0.2))

    right.setAttribute("fill", darkenColor(color, 0.2))
    right.setAttribute("stroke", darkenColor(color, 0.3))
}

function applyStripedShadingToCircle(circle: SVGElement, color: string, patternId?: string): void {
    if (patternId) circle.setAttribute("fill", `url(#${patternId})`)
    else circle.setAttribute("fill", "none")
    circle.setAttribute("stroke", color)
    circle.setAttribute("stroke-width", "2")
}

function applyStripedShadingToDiamond(
    diamond: ReturnType<typeof createDiamondShape>,
    color: string,
    patternId?: string
): void {
    const { topFacet, bottomFacet, glare } = diamond

    for (const facet of [topFacet, bottomFacet]) {
        if (!facet) continue
        if (patternId) facet.setAttribute("fill", `url(#${patternId})`)
        else facet.setAttribute("fill", "none")
        facet.setAttribute("stroke", color)
        facet.setAttribute("stroke-width", "3")
        facet.setAttribute("stroke-linejoin", "round")
        facet.setAttribute("stroke-linecap", "round")
    }

    glare.setAttribute("fill", "#ffffff")
    glare.setAttribute("fill-opacity", "0.10")
    glare.setAttribute("stroke", "none")
}

function applyStripedShadingToRectangle(
    rect: ReturnType<typeof createRectangularShape>,
    color: string,
    patternId?: string
): void {
    const { element } = rect
    const childEls = Array.from(element.children) as SVGElement[]

    for (const child of childEls) {
        if (patternId) child.setAttribute("fill", `url(#${patternId})`)
        else child.setAttribute("fill", "none")
        child.setAttribute("stroke", color)
        child.setAttribute("stroke-width", "3")
    }
}

function applyOutlineShadingToCircle(circle: SVGElement, color: string): void {
    circle.setAttribute("fill", "none")
    circle.setAttribute("stroke", color)
    circle.setAttribute("stroke-width", "4")
}

function applyOutlineShadingToDiamond(
    diamond: ReturnType<typeof createDiamondShape>,
    color: string
): void {
    const { topFacet, bottomFacet, glare } = diamond

    for (const facet of [topFacet, bottomFacet]) {
        if (!facet) continue
        facet.setAttribute("fill", "none")
        facet.setAttribute("stroke", color)
        facet.setAttribute("stroke-width", "4")
        facet.setAttribute("stroke-linejoin", "round")
        facet.setAttribute("stroke-linecap", "round")
    }

    glare.setAttribute("fill", "#ffffff")
    glare.setAttribute("fill-opacity", "0.06")
    glare.setAttribute("stroke", "none")
}

function applyOutlineShadingToRectangle(
    rect: ReturnType<typeof createRectangularShape>,
    color: string
): void {
    const { element } = rect
    const childEls = Array.from(element.children) as SVGElement[]

    for (const child of childEls) {
        child.setAttribute("fill", "none")
        child.setAttribute("stroke", color)
        child.setAttribute("stroke-width", "4")
    }
}

function applyRoundedEdges(element: SVGElement): void {
    const children = (element as SVGGElement).children

    if (children && children.length > 0) {
        const childEls = Array.from(children) as SVGElement[]
        for (const child of childEls) {
            child.setAttribute("stroke-linejoin", "round")
            child.setAttribute("stroke-linecap", "round")
        }
    } else {
        element.setAttribute("stroke-linejoin", "round")
        element.setAttribute("stroke-linecap", "round")
    }
}

function createAndShadeShape(shape: number, color: string, shading: number): SVGElement {
    const patternId = shading === 1 ? getOrCreateStripedPattern(color) : undefined
    const gradientId = shape === 0 && (shading === 0 || shading === 2) ?
        getOrCreateSphereGradient(color) : undefined

    return createShapeByType(shape, color, shading, patternId, gradientId)
}

function createShapeByType(shape: number, color: string, shading: number, patternId?: string, gradientId?: string): SVGElement {
    if (shape === 0) { // Circle
        return createAndShadeCircle(color, shading, patternId, gradientId)
    } else if (shape === 1) { // Diamond
        return createAndShadeDiamond(color, shading, patternId)
    } else { // Rectangle
        return createAndShadeRectangle(color, shading, patternId)
    }
}

function createAndShadeCircle(color: string, shading: number, patternId?: string, gradientId?: string): SVGElement {
    const circle = createCircleShape()

    if (shading === 0) applySolidShadingToCircle(circle, color, gradientId)
    else if (shading === 1) applyStripedShadingToCircle(circle, color, patternId)
    else applyOutlineShadingToCircle(circle, color)

    applyRoundedEdges(circle)
    return circle
}

function createAndShadeDiamond(color: string, shading: number, patternId?: string): SVGElement {
    const diamond = createDiamondShape(color)

    if (shading === 0) applySolidShadingToDiamond(diamond, color)
    else if (shading === 1) applyStripedShadingToDiamond(diamond, color, patternId)
    else applyOutlineShadingToDiamond(diamond, color)

    applyRoundedEdges(diamond.element)
    return diamond.element
}

function createAndShadeRectangle(color: string, shading: number, patternId?: string): SVGElement {
    const rect = createRectangularShape()

    if (shading === 0) applySolidShadingToRectangle(rect, color)
    else if (shading === 1) applyStripedShadingToRectangle(rect, color, patternId)
    else applyOutlineShadingToRectangle(rect, color)

    return rect.element
}

export function createSymbolSVG(shape: number, colorIdx: number, shading: number): SVGSVGElement {
    const color = colorForIndex(colorIdx)
    const svg = document.createElementNS(SVG_NS, "svg")
    svg.setAttribute("viewBox", "0 0 100 100")
    svg.setAttribute("role", "img")

    const shapeEl = createAndShadeShape(shape, color, shading)
    svg.appendChild(shapeEl)
    return svg
}

export default createSymbolSVG
