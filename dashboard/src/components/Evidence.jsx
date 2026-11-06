import { useState } from 'react'
import { ImageOff } from 'lucide-react'
import { pairEvidence, evidenceUrl } from '../format.js'
import CompareSlider from './CompareSlider.jsx'

// One screenshot with a fallback when the file is missing or fails to load.
function Shot({ path, label }) {
  const [failed, setFailed] = useState(false)
  if (!path)
    return <div className="shot-missing" data-testid="shot-missing"><ImageOff size={20} aria-hidden="true" />{label === 'After' ? 'No retest screenshot' : 'No baseline screenshot'}</div>
  if (failed)
    return (
      <div className="shot-missing" data-testid="shot-failed" role="img" aria-label={`${label} screenshot failed to load`}>
        <ImageOff size={20} aria-hidden="true" />Image failed to load<code>{path}</code>
      </div>
    )
  const url = evidenceUrl(path)
  return (
    <a href={url} target="_blank" rel="noreferrer" className="shot-link viewfinder">
      <img src={url} alt={`${label} screenshot: ${path}`} loading="lazy" onError={() => setFailed(true)} />
    </a>
  )
}

const viewportLabel = (v) => (v === 'all' ? 'All sizes' : v.replace(/^(desktop|mobile)_(\d+)x(\d+)$/, '$1 $2×$3'))

export default function Evidence({ evidence }) {
  const pairs = pairEvidence(evidence)
  const viewports = [...new Set(pairs.map((p) => p.viewport || 'other'))]
  const [vp, setVp] = useState('all')
  if (pairs.length === 0)
    return <div className="empty" data-testid="evidence-empty"><ImageOff size={28} aria-hidden="true" /><p>No screenshots were captured for this run.</p></div>

  // Pairs with a retest "after" image (the slider) first: that's where the fix is visible.
  const shown = (vp === 'all' ? pairs : pairs.filter((p) => (p.viewport || 'other') === vp))
    .slice().sort((a, b) => Number(!!b.after) - Number(!!a.after))
  return (
    <>
      {viewports.length > 1 && (
        <div className="chips" role="group" aria-label="Screen size">
          {['all', ...viewports].map((v) => (
            <button key={v} type="button" className="chip" aria-pressed={vp === v} onClick={() => setVp(v)}>{viewportLabel(v)}</button>
          ))}
        </div>
      )}
      <div className="pairs">
        {shown.map((p) => (
          <figure key={p.key} className="pair panel" data-testid={`evidence-pair-${p.key}`}>
            <figcaption><span className="mono">{p.viewport || 'unknown size'}</span><span>{p.page}</span></figcaption>
            {p.before && p.after ? (
              <CompareSlider before={evidenceUrl(p.before)} after={evidenceUrl(p.after)} label={`${p.viewport} ${p.page}`} />
            ) : (
              <div>
                <div className="shot-label before">{p.before ? 'Before' : 'After'}</div>
                <Shot key={p.before || p.after || 'none'} path={p.before || p.after} label={p.before ? 'Before' : 'After'} />
              </div>
            )}
          </figure>
        ))}
      </div>
    </>
  )
}
