import { useEffect, useState, useMemo } from 'react'
import { ImageOff } from 'lucide-react'
import { pairEvidence, evidenceUrl } from '../format.js'
import { fetchImageUrl } from '../api.js'
import CompareSlider from './CompareSlider.jsx'

// Backend-generated image (heatmap, defect overlay): these routes need the login token.
function AuthImg({ path, alt, missing }) {
  const [state, setState] = useState({ url: null, failed: false })
  useEffect(() => {
    let live = true
    let made = null
    setState({ url: null, failed: false })
    fetchImageUrl(path)
      .then((u) => { made = u; if (live) setState({ url: u, failed: false }); else URL.revokeObjectURL(u) })
      .catch(() => { if (live) setState({ url: null, failed: true }) })
    return () => { live = false; if (made) URL.revokeObjectURL(made) }
  }, [path])
  if (state.failed) return <div className="shot-missing" role="img" aria-label={missing}><ImageOff size={20} aria-hidden="true" />{missing}</div>
  if (!state.url) return <div className="skeleton skeleton-row" aria-busy="true" />
  return <img src={state.url} alt={alt} className="diag-img" />
}

const diagPath = (runId, kind, p) =>
  `/runs/${encodeURIComponent(runId)}/${kind}?viewport=${encodeURIComponent(p.viewport || 'desktop_1440x900')}&page=${encodeURIComponent(p.page || 'home')}`

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
      <img src={url} alt={`${label} screenshot: ${path}`} loading="lazy" decoding="async" onError={() => setFailed(true)} />
    </a>
  )
}

const viewportLabel = (v) => (v === 'all' ? 'All sizes' : v.replace(/^(desktop|mobile)_(\d+)x(\d+)$/, '$1 $2×$3'))

export default function Evidence({ evidence, runId }) {
  const pairs = useMemo(() => pairEvidence(evidence), [evidence])
  const viewports = useMemo(() => [...new Set(pairs.map((p) => p.viewport || 'other'))], [pairs])
  const [vp, setVp] = useState('all')
  const [viewMode, setViewMode] = useState('slider')

  // Pairs with a retest "after" image (the slider) first: that's where the fix is visible.
  const shown = useMemo(
    () =>
      (vp === 'all' ? pairs : pairs.filter((p) => (p.viewport || 'other') === vp))
        .slice()
        .sort((a, b) => Number(!!b.after) - Number(!!a.after)),
    [pairs, vp]
  )
  if (pairs.length === 0)
    return <div className="empty" data-testid="evidence-empty"><ImageOff size={28} aria-hidden="true" /><p>No screenshots were captured for this run.</p></div>
  return (
    <>
      <div className="evidence-toolbar">
        {viewports.length > 1 && (
          <div className="chips" role="group" aria-label="Screen size">
            {['all', ...viewports].map((v) => (
              <button key={v} type="button" className="chip" aria-pressed={vp === v} onClick={() => setVp(v)}>{viewportLabel(v)}</button>
            ))}
          </div>
        )}
        <div className="chips view-modes" role="group" aria-label="Visual Diff Mode">
          {[
            { id: 'slider', label: '⇄ Compare Slider' },
            { id: 'side', label: '◫ Side-by-Side' },
            { id: 'heatmap', label: 'Diff Heatmap' },
            { id: 'annotated', label: '⛶ Defect Overlay' },
          ].map((m) => (
            <button key={m.id} type="button" className="chip" aria-pressed={viewMode === m.id} onClick={() => setViewMode(m.id)}>
              {m.label}
            </button>
          ))}
        </div>
      </div>
      <div className="pairs">
        {shown.map((p) => (
          <figure key={p.key} className={`pair panel${p.viewport?.startsWith('mobile') ? ' is-mobile' : ''}`} data-testid={`evidence-pair-${p.key}`}>
            <figcaption><span className="mono">{p.viewport || 'unknown size'}</span><span>{p.page}</span></figcaption>
            {viewMode === 'heatmap' && runId ? (
              <div className="diag-view">
                <div className="shot-label heatmap">Visual Diff Heatmap (Pixel-Level Anomaly)</div>
                <AuthImg path={diagPath(runId, 'heatmap', p)} alt={`Diff heatmap: ${p.viewport} ${p.page}`}
                  missing="No heatmap: this page wasn't re-tested after the fix" />
              </div>
            ) : viewMode === 'annotated' && runId ? (
              <div className="diag-view">
                <div className="shot-label annotated">Detected Defect Remediations Overlay</div>
                <AuthImg path={diagPath(runId, 'annotated', p)} alt={`Defects marked: ${p.viewport} ${p.page}`}
                  missing="No defect overlay for this screenshot" />
              </div>
            ) : viewMode === 'side' && p.before && p.after ? (
              <div className="side-by-side">
                <div>
                  <div className="shot-label before">Before (Baseline)</div>
                  <Shot path={p.before} label="Before" />
                </div>
                <div>
                  <div className="shot-label after">After (Retest)</div>
                  <Shot path={p.after} label="After" />
                </div>
              </div>
            ) : p.before && p.after ? (
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
