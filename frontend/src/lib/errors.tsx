import React, { createContext, useContext, useRef, useState, useCallback } from 'react'

export type Toast = { id: number, message: string, severity?: 'info' | 'success' | 'error', duration?: number }

const ToastCtx = createContext<{ add: (t: Omit<Toast, 'id'>) => void } | null>(null)

export function useToasts() {
    const ctx = useContext(ToastCtx)
    if (!ctx) throw new Error('useToasts must be used within ToastProvider')
    return ctx
}

export function ToastProvider({ children }: { readonly children: React.ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([])
    const idRef = useRef(1)
    const removeToastById = useCallback((id: number) => setToasts((arr) => arr.filter((x) => x.id !== id)), [])
    const add = useCallback((t: Omit<Toast, 'id'>) => {
        const id = idRef.current++
        const toast: Toast = { id, severity: 'info', duration: 4000, ...t }
        setToasts((arr) => [...arr, toast])
        if (toast.duration && toast.duration > 0) {
            const handle = setTimeout(() => removeToastById(id), toast.duration)
            return () => clearTimeout(handle)
        }
    }, [])
    const ctxValue = React.useMemo(() => ({ add }), [add])
    return (
        <ToastCtx.Provider value={ctxValue}>
            {children}
            <div id="toast-container" className="toast-container">
                {toasts.map(t => {
                    let startX = 0
                    let startY = 0
                    const onTouchStart: React.TouchEventHandler<HTMLDivElement> = (e) => {
                        const first = e.touches && e.touches.length > 0 ? e.touches[0] : null
                        if (first) {
                            startX = first.clientX
                            startY = first.clientY
                        }
                    }
                    const onTouchEnd: React.TouchEventHandler<HTMLDivElement> = (e) => {
                        const touch = e.changedTouches?.[0]
                        if (!touch) return
                        const dx = touch.clientX - startX
                        const dy = touch.clientY - startY
                        // Dismiss on horizontal swipe over threshold and dominant over vertical
                        if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) {
                            removeToastById(t.id)
                        }
                    }
                    const onKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            removeToastById(t.id)
                        }
                    }
                    return (
                        <div
                            key={t.id}
                            className={`toast toast-${t.severity ?? 'info'} toast-show`}
                            role="status"
                            tabIndex={0}
                            onClick={() => removeToastById(t.id)}
                            onTouchStart={onTouchStart}
                            onTouchEnd={onTouchEnd}
                            onKeyDown={onKeyDown}
                            aria-label={`Notification: ${t.message}. Tap or press Enter to dismiss.`}
                        >
                            <div className="toast-content">
                                <span className="toast-message">{t.message}</span>
                            </div>
                        </div>
                    )
                })}
            </div>
        </ToastCtx.Provider>
    )
}
