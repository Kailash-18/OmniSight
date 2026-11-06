import { createContext, useCallback, useContext, useState } from 'react'
import { CircleCheck, TriangleAlert, Info } from 'lucide-react'

const ToastContext = createContext(() => {})
export const useToast = () => useContext(ToastContext)
const ICONS = { good: CircleCheck, bad: TriangleAlert, info: Info }

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, tone = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, message, tone }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite" data-testid="toasts">
        {toasts.map(({ id, message, tone }) => {
          const Icon = ICONS[tone] || Info
          return <div key={id} className={`toast tone-${tone}`}><Icon size={18} aria-hidden="true" />{message}</div>
        })}
      </div>
    </ToastContext.Provider>
  )
}
