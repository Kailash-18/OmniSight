import { useEffect, useRef, useState } from 'react'
import { Play, Link2, LoaderCircle, Activity, Bug, Wrench, GitPullRequest, ArrowRight } from 'lucide-react'
import { DATA_SOURCE, fetchMetricsSummary, getActiveRun, getRun, listRuns, startRun } from '../api.js'
import { isActiveStatus, relativeTime, stats } from '../lifecycle.js'
import Lifecycle from './Lifecycle.jsx'
import StatusBadge from './StatusBadge.jsx'
import MockTag from './MockTag.jsx'
import { useToast } from './Toast.jsx'

const DEFAULT_TARGET = 'http://localhost:5173'
const POLL_MS = 2000
const PRESETS = [
  { label: 'Local Store (:5173)', url: 'http://localhost:5173' },
  { label: 'Flipkart (flipkart.com)', url: 'https://www.flipkart.com/' },
  { label: 'Staging Mock', url: 'http://staging.internal:5173' },
]
const INTERACTION = new Set(['broken_link', 'click_error', 'no_effect'])
const CATEGORY_LABELS = {
  element_overlap: 'Overlap', element_clipping: 'Clipped', element_obstruction: 'Covered',
  contrast_issue: 'Contrast', layout_overflow: 'Overflow', broken_link: 'Broken link',
  click_error: 'Click error', no_effect: 'Does nothing',
}

function RunLauncherBar({ onStarted, running }) {
  const [url, setUrl] = useState(DEFAULT_TARGET)
  const [retest, setRetest] = useState(true)
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setStarting(true)
    try {
      const r = await startRun(url, { retest })
      onStarted(r.run_id)
    } catch (err) {
      setError(/allowed target hosts/i.test(err.message)
        ? 'OmniSight can only test sites on the allowed list (by default, apps on localhost such as the store at http://localhost:5173).'
        : err.message)
    } finally {
      setStarting(false)
    }
  }

  const disabled = DATA_SOURCE === 'mock' || running || starting || !url.trim()
  return (
    <form className={`launcher panel${running ? ' is-running' : ''}`} onSubmit={submit} data-testid="run-launcher">
      <div className="launcher-head">
        <h2>Test a site</h2>
        <p className="muted">Paste the app’s address. OmniSight walks it on 4 screen sizes, clicks every button, and proposes a fix for what it finds.</p>
      </div>
      <div className="launcher-row">
        <span className="input-wrap grow">
          <Link2 size={18} className="input-icon" aria-hidden="true" />
          <input className="input with-icon" value={url} onChange={(e) => setUrl(e.target.value)} aria-label="Site address"
            placeholder="http://localhost:5173" inputMode="url" spellCheck="false" data-testid="run-target" />
        </span>
        <label className="check"><input type="checkbox" checked={retest} onChange={(e) => setRetest(e.target.checked)} data-testid="run-retest" />Check the fix</label>
        <button className="btn btn-primary" disabled={disabled} data-testid="run-start">
          {starting || running ? <LoaderCircle className="spin" size={18} aria-hidden="true" /> : <Play size={18} aria-hidden="true" />}
          {running ? 'Test running…' : 'Run test'}
        </button>
      </div>
      <div className="launcher-presets" role="group" aria-label="Target Presets">
        <span className="preset-label">Quick Presets:</span>
        {PRESETS.map((p) => (
          <button
            key={p.url}
            type="button"
            className={`btn-pill ${url.trim() === p.url ? 'is-active' : ''}`}
            onClick={() => { setUrl(p.url); setError(null); }}
            data-testid={`preset-${p.label.split(' ')[0].toLowerCase()}`}
          >
            {p.label}
          </button>
        ))}
      </div>
      {DATA_SOURCE === 'mock' && <p className="muted small">Tests can only be started in live mode. These are sample runs.</p>}
      {error && (
        <div className="alert alert-with-action" role="alert" data-testid="run-start-error">
          <span>{error}</span>
          <button
            type="button"
            className="btn-text alert-action"
            onClick={() => { setUrl(DEFAULT_TARGET); setError(null); }}
            data-testid="reset-target-btn"
          >
            Reset to Local Store
          </button>
        </div>
      )}
    </form>
  )
}

function StatTiles({ runs, metrics }) {
  const s = stats(runs)
  const diff = metrics?.average_diff_reduction
  return (
    <div className="tiles" data-testid="stat-tiles">
      <div className="tile panel"><span className="tile-value">{s.total}</span><Activity size={18} className="tile-icon" aria-hidden="true" /><span className="tile-label">Test runs</span></div>
      <div className="tile panel accent"><span className="tile-value">{s.bugs}</span><Bug size={18} className="tile-icon" aria-hidden="true" /><span className="tile-label">Bugs found</span></div>
      <div className="tile panel fix">
        <span className="tile-value">{s.fixRate}</span><Wrench size={18} className="tile-icon" aria-hidden="true" /><span className="tile-label">Fixed and verified</span>
        {diff > 0 && <span className="tile-note">Average pixel change after fix: {(diff * 100).toFixed(1)}%</span>}
      </div>
      <div className="tile panel"><span className="tile-value">{s.prs}</span><GitPullRequest size={18} className="tile-icon" aria-hidden="true" /><span className="tile-label">Pull requests</span></div>
    </div>
  )
}

function DefectBars({ categories }) {
  const rows = Object.entries(categories || {}).sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...rows.map(([, n]) => n))
  return (
    <section className="panel" data-testid="defect-breakdown">
      <div className="section-head"><h2>What OmniSight finds</h2></div>
      {rows.length === 0 ? (
        <p className="muted small">Bug types appear here after the first run.</p>
      ) : (
        <div className="bars">
          {rows.map(([cat, n]) => (
            <div key={cat} className={`bar-row${INTERACTION.has(cat) ? ' interaction' : ''}`}>
              <span title={cat}>{CATEGORY_LABELS[cat] || cat}</span>
              <span className="bar-track"><span className="bar-fill" style={{ width: `${(n / max) * 100}%` }} /></span>
              <b>{n}</b>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function LiveRunCard({ run, live, link }) {
  if (!run) return null
  const findings = (run.findings || []).length
  return (
    <section className={`live-card panel${live ? ' is-live' : ''}`} data-testid="live-run-card" aria-live="polite">
      <div className="live-head">
        <span className={`pill ${live ? 'tone-info live' : 'tone-neutral'}`}><span className="dot" aria-hidden="true" />{live ? 'Running now' : 'Latest run'}</span>
        <a className="mono" {...link(`/runs/${encodeURIComponent(run.run_id)}`)}>{run.run_id}</a>
        <StatusBadge status={run.status} />
      </div>
      {live && <div className="progress" aria-hidden="true"><span /></div>}
      <Lifecycle run={run} />
      <p className="muted small">
        {`${findings} ${findings === 1 ? 'finding' : 'findings'}${live ? ' so far' : ''}. `}
        {run.steps?.length ? `Last step: ${run.steps.at(-1).replaceAll('_', ' ')}.` : 'Opening the browser…'}
      </p>
    </section>
  )
}

export default function Overview({ link }) {
  const [runs, setRuns] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState(null)
  const [liveId, setLiveId] = useState(null)
  const [liveRun, setLiveRun] = useState(null)
  const toast = useToast()
  const announced = useRef(false)

  const loadRuns = () => {
    listRuns().then((r) => { setRuns(r); setError(null) }).catch(setError)
    fetchMetricsSummary().then(setMetrics).catch(() => {})
  }

  useEffect(() => {
    loadRuns()
    getActiveRun().then((a) => a.run_id && setLiveId(a.run_id)).catch(() => {})
  }, [])

  // Show the latest run when nothing is running.
  useEffect(() => {
    if (!liveId && !liveRun && runs?.length) getRun(runs[0].run_id).then(setLiveRun).catch(() => {})
  }, [runs])

  // Poll the launched run until the backend reports no active run, then refresh and announce.
  useEffect(() => {
    if (!liveId) return undefined
    let stop = false
    const tick = async () => {
      try {
        const [run, active] = await Promise.all([getRun(liveId), getActiveRun()])
        if (stop) return
        setLiveRun(run)
        if (active.run_id === liveId) return
        if (!announced.current) {
          announced.current = true
          const n = (run.findings || []).length
          if (run.status === 'failed') toast(`Test failed: ${run.error?.split('\n')[0] || 'open the run for details'}`, 'bad')
          else toast(`Test finished with ${n} ${n === 1 ? 'finding' : 'findings'}`, 'good')
        }
        setLiveId(null)
        loadRuns()
      } catch {
        /* a 401 is handled globally; anything else retries on the next tick */
      }
    }
    tick()
    const id = setInterval(tick, POLL_MS)
    return () => { stop = true; clearInterval(id) }
  }, [liveId])

  const onStarted = (runId) => {
    announced.current = false
    setLiveId(runId)
    toast('Test started', 'info')
    loadRuns()
  }

  return (
    <div className="overview" data-testid="overview">
      <header className="page-head">
        <div><h1>Overview</h1><p className="muted">Start a test, watch it run, then review the fix.</p></div>
      </header>
      <RunLauncherBar onStarted={onStarted} running={!!liveId} />
      {error ? (
        <div className="panel empty" role="alert" data-testid="runs-error">
          <h2>Couldn’t load runs</h2>
          <p>{error.message}. Check that the backend is running on port 8000.</p>
          <button type="button" className="btn" onClick={loadRuns} data-testid="runs-retry">Try again</button>
        </div>
      ) : runs === null ? (
        <div className="tiles" aria-busy="true">{[0, 1, 2, 3].map((i) => <div key={i} className="tile panel skeleton" />)}</div>
      ) : (
        <StatTiles runs={runs} metrics={metrics} />
      )}
      <LiveRunCard run={liveRun} live={!!liveId} link={link} />
      <div className="overview-grid">
        <section className="panel" data-testid="recent-runs">
          <div className="section-head"><h2>Recent runs</h2><a className="link-arrow" {...link('/runs')}>All runs<ArrowRight size={16} aria-hidden="true" /></a></div>
          {runs?.length === 0 && <p className="muted" data-testid="runs-empty">No runs yet. Start one above.</p>}
          <ul className="recent-list">
            {(runs || []).slice(0, 6).map((r) => (
              <li key={r.run_id}>
                <span><a className="mono" {...link(`/runs/${encodeURIComponent(r.run_id)}`)}>{r.run_id}</a><MockTag /></span>
                <StatusBadge status={r.status} />
                <span className="recent-meta">{r.issue_count} {r.issue_count === 1 ? 'bug' : 'bugs'}, {relativeTime(r.start_time)}</span>
              </li>
            ))}
          </ul>
        </section>
        <DefectBars categories={metrics?.defect_categories} />
      </div>
    </div>
  )
}
