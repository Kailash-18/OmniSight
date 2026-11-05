import { statusMeta } from '../format.js'
import { isActiveStatus } from '../lifecycle.js'

export default function StatusBadge({ status }) {
  const { label, tone } = statusMeta(status)
  return (
    <span className={`pill tone-${tone}${isActiveStatus(status) ? ' live' : ''}`} data-testid="status-badge">
      <span className="dot" aria-hidden="true" />{label}
    </span>
  )
}
