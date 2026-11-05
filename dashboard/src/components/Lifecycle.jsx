import { Check, X, Minus } from 'lucide-react'
import { lifecycle } from '../lifecycle.js'

export default function Lifecycle({ run }) {
  return (
    <ol className="lifecycle" data-testid="lifecycle" aria-label="Run progress">
      {lifecycle(run).map((s) => (
        <li key={s.key} className={`step ${s.state}`} aria-current={s.state === 'current' ? 'step' : undefined}>
          <span className="step-dot" aria-hidden="true">
            {s.state === 'done' ? <Check size={13} strokeWidth={3} /> : s.state === 'failed' ? <X size={13} strokeWidth={3} /> : s.state === 'skipped' ? <Minus size={13} /> : null}
          </span>
          <span className="step-label">{s.label}<span className="visually-hidden"> ({s.state})</span></span>
        </li>
      ))}
    </ol>
  )
}
