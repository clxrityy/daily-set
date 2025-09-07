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
                {toasts.map(t => (
                    <div key={t.id} className={`toast toast-${t.severity ?? 'info'} toast-show`}>
                        <div className="toast-content">
                            <span className="toast-message">{t.message}</span>
                            <button
                                className="toast-close"
                                aria-label="Close"
                                onClick={() => removeToastById(t.id)}
                            >
                                &times;
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </ToastCtx.Provider>
    )
}
