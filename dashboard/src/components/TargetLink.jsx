import { safeUrl } from '../format.js'

// The store URL a run tested. Plain text if it isn't a safe http(s) URL.
export default function TargetLink({ target }) {
  const url = safeUrl(target)
  if (!url) return <span>{target || '—'}</span>
  return (
    <a href={url} target="_blank" rel="noreferrer" data-testid="target-link">
      {target}<span className="visually-hidden"> (opens in a new tab)</span>
    </a>
  )
}
