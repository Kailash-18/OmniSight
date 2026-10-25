import { statusMeta } from '../format.js'

export default function StatusBadge({ status }) {
  const { label, tone } = statusMeta(status)
  return <span className={`badge tone-${tone}`} data-testid="status-badge" data-status={status}>{label}</span>
}
