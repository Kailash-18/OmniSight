import { useState } from 'react'
import { pairEvidence, evidenceUrl } from '../format.js'

// One screenshot with a fallback when the file is missing or fails to load.
function Shot({ path, label }) {
  const [failed, setFailed] = useState(false)
  if (!path)
    return <div className="shot-missing" data-testid="shot-missing">{label === 'After' ? 'No retest screenshot' : 'No baseline screenshot'}</div>
  if (failed)
    return (
      <div className="shot-missing" data-testid="shot-failed" role="img" aria-label={`${label} screenshot failed to load`}>
        Image failed to load
        <code>{path}</code>
      </div>
    )
  const url = evidenceUrl(path)
  return (
    <a href={url} target="_blank" rel="noreferrer" className="shot-link">
      <img src={url} alt={`${label} screenshot: ${path}`} loading="lazy" onError={() => setFailed(true)} />
    </a>
  )
}

export default function Evidence({ evidence }) {
  const pairs = pairEvidence(evidence)
  if (pairs.length === 0) return <p className="muted" data-testid="evidence-empty">No screenshots were captured for this run.</p>

  return (
    <div className="pairs">
      {pairs.map((p) => (
        <figure key={p.key} className="pair" data-testid={`evidence-pair-${p.key}`}>
          <figcaption>
            <span className="mono">{p.viewport || 'unknown viewport'}</span> · {p.page}
          </figcaption>
          <div className="pair-grid">
            <div>
              <div className="shot-label before">Before</div>
              {/* key resets the failed state if the path changes */}
              <Shot key={p.before || 'none-b'} path={p.before} label="Before" />
            </div>
            <div>
              <div className="shot-label after">After</div>
              <Shot key={p.after || 'none-a'} path={p.after} label="After" />
            </div>
          </div>
        </figure>
      ))}
    </div>
  )
}
