// Lightweight haptics/vibration helpers with throttling and feature detection
// Uses navigator.vibrate when available; silently no-ops otherwise.
// Patterns follow common UX: light tap, success burst, error buzz.

let lastVibe = 0
const MIN_GAP = 40 // ms, avoid spamming

function vib(pattern: number | number[]) {
    try {
        const now = Date.now()
        if (now - lastVibe < MIN_GAP) return
        lastVibe = now
        const navAny: any = typeof navigator !== 'undefined' ? (navigator as unknown as any) : null
        if (navAny && typeof navAny.vibrate === 'function') {
            navAny.vibrate(pattern)
        }
    } catch {
        // ignore
    }
}

export const haptic = {
    light() {
        vib(8)
    },
    success() {
        vib([10, 20, 10])
    },
    error() {
        vib([30, 40, 30])
    },
}

export default haptic
