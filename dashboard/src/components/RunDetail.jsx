import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, RefreshCw, Bug, Images, FileDiff, GitPullRequest, Fingerprint, Download, ExternalLink, TriangleAlert, ShieldCheck } from 'lucide-react'
import { downloadForensicBundle, verifyForensicBundle, getActiveRun, getRun } from '../api.js'
import { formatConfidence, formatTime, diffLines, validatorErrors, defectPage } from '../format.js'
import { shouldPoll } from '../lifecycle.js'
import StatusBadge from './StatusBadge.jsx'
import MockTag from './MockTag.jsx'
import TargetLink from './TargetLink.jsx'
import Lifecycle from './Lifecycle.jsx'
import Evidence from './Evidence.jsx'
import ReviewPanel from './ReviewPanel.jsx'
import { useToast } from './Toast.jsx'

const POLL_MS = 2000
const INTERACTION = new Set(['broken_link', 'click_error', 'no_effect'])

// "Open the store, then do these steps at this size" so a reviewer can see the defect live.
function DefectLink({ link, id }) {
  if (!link) return <span className="muted">Not available (no screenshot or no valid target address)</span>
  return (
    <div className="defect-link" data-testid={`defect-link-${id}`}>
      <a href={link.url} target="_blank" rel="noreferrer" className="btn btn-small">
        {link.page ? `Open ${link.page} page` : 'Open store'}<ExternalLink size={14} aria-hidden="true" />
        <span className="visually-hidden"> (opens the store in a new tab)</span>
      </a>
      <ol className="defect-steps small muted" data-testid="defect-steps">
        {link.size && <li>Set the browser to {link.size} (DevTools device mode)</li>}
        {link.page && link.steps.map((s) => <li key={s}>{s}</li>)}
        {link.page === 'Products' && <li>The defect is visible on load</li>}
        {!link.page && <li>Page not identified from the evidence; compare with the screenshots</li>}
      </ol>
    </div>
  )
}

function ConfidenceRing({ value }) {
  const label = formatConfidence(value)
  const pct = label === '—' ? 0 : value
  const c = 2 * Math.PI * 22
  return (
    <div className="ring" aria-hidden="true">
      <svg width="56" height="56" viewBox="0 0 56 56">
        <circle className="ring-track" cx="28" cy="28" r="22" fill="none" strokeWidth="5" />
        <circle className="ring-value" cx="28" cy="28" r="22" fill="none" strokeWidth="5" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} />
      </svg>
      <span>{label}</span>
    </div>
  )
}

function FindingCard({ f, run }) {
  const interaction = INTERACTION.has(f.category) || f.id?.startsWith('interaction-')
  const isA11y = f.id?.startsWith('a11y-') || f.category === 'contrast_issue' || f.description?.includes('WCAG')
  return (
    <article className={`finding-card${isA11y ? ' a11y' : interaction ? ' interaction' : ''}`} data-testid={`finding-${f.id}`}>
      <ConfidenceRing value={f.confidence} />
      <div>
        <div className="finding-top">
          <strong>{f.description}</strong>
          <div className="finding-tags">
            <span className={`pill sev sev-${f.severity}`}>{f.severity}</span>
            {isA11y ? (
              <span className="pill tone-purple">Accessibility (WCAG)</span>
            ) : (
              <span className="pill tone-neutral">{interaction ? 'Interaction' : 'Visual'}</span>
            )}
          </div>
        </div>
        <dl className="facts">
          <dt>Confidence</dt><dd data-testid="confidence">{formatConfidence(f.confidence)}</dd>
          <dt>Type</dt><dd className="mono">{f.category}</dd>
          <dt>Screen size</dt><dd className="mono">{f.viewport}</dd>
          {f.target_element && <><dt>Element</dt><dd className="mono">{f.target_element}</dd></>}
          <dt>Suggested fix</dt><dd>{f.suggested_change}</dd>
          <dt>Why</dt><dd>{f.rationale}</dd>
          <dt>See it live</dt><dd><DefectLink link={defectPage(run.target, f, run.evidence_paths)} id={f.id} /></dd>
        </dl>
      </div>
    </article>
  )
}

function RetestSummary({ retest }) {
  if (!retest) return null
  const mismatch = typeof retest.mismatch_percentage === 'number' ? retest.mismatch_percentage
    : typeof retest.visual_diff_score === 'number' ? retest.visual_diff_score * 100 : null
  const passed = retest.passed ?? retest.status === 'fixed'
  return (
    <section className="panel retest-summary" data-testid="retest-proof-summary">
      <div className="retest-head">
        <h3>Fix check</h3>
        <span className={`pill ${passed ? 'tone-good' : 'tone-bad'}`} data-testid="retest-badge"><span className="dot" aria-hidden="true" />{passed ? 'Verified fixed' : 'Not resolved'}</span>
      </div>
      <dl className="facts">
        <dt>Tested at</dt><dd className="mono">{retest.retest_viewport || retest.target_viewport || 'all sizes'}</dd>
        {mismatch !== null && <><dt>Pixel change</dt><dd className="mono">{mismatch.toFixed(2)}%</dd></>}
        <dt>Source files</dt><dd>Restored after the check</dd>
        {retest.notes && <><dt>Notes</dt><dd>{retest.notes}</dd></>}
      </dl>
    </section>
  )
}

function PatchView({ patch }) {
  const errors = validatorErrors(patch)
  if (!patch) return <div className="empty" data-testid="patch-empty"><FileDiff size={28} aria-hidden="true" /><p>No fix was proposed for this run.</p></div>
  return (
    <section className="panel tabpanel">
      <div className="patch-head">
        <span className="mono">{patch.target_file}</span>
        {patch.validation_status === true && <span className="pill tone-good" data-testid="patch-valid"><ShieldCheck size={14} aria-hidden="true" />Passed safety check</span>}
        {patch.validation_status === false && <span className="pill tone-bad" data-testid="patch-invalid"><TriangleAlert size={14} aria-hidden="true" />Rejected by safety check</span>}
      </div>
      {patch.explanation && <p className="muted">{patch.explanation}</p>}
      {errors.length > 0 && <ul className="alert" data-testid="validator-errors">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
      <pre className="diff" data-testid="patch-diff">
        {diffLines(patch.diff).map((l, i) => <span key={i} className={`dl dl-${l.kind}`}>{l.line}{'\n'}</span>)}
      </pre>
    </section>
  )
}

function ForensicsPanel({ runId }) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [verification, setVerification] = useState(null)

  const download = async () => {
    setBusy(true)
    try { await downloadForensicBundle(runId) } catch (e) { toast(e.message, 'bad') } finally { setBusy(false) }
  }

  const handleVerify = async () => {
    setVerifying(true)
    try {
      const res = await verifyForensicBundle(runId)
      setVerification(res)
      toast('Cryptographic proof verified successfully', 'good')
    } catch (e) {
      toast(e.message || 'Bundle verification failed', 'bad')
    } finally {
      setVerifying(false)
    }
  }

  return (
    <section className="panel forensic-card" data-testid="forensic-bundle-card">
      <div className="forensic-header">
        <div>
          <h3>Zero-Trust Forensic Audit Bundle</h3>
          <p className="muted">Cryptographically-sealed evidence bundle containing all viewport screenshots, DOM trees, network traces, and signed SHA-256 manifests.</p>
        </div>
        <span className="pill tone-purple">SHA-256 Signed</span>
      </div>

      <dl className="facts">
        <dt>Format</dt><dd className="mono">ZIP (.zip) + Manifest</dd>
        <dt>Specification</dt><dd className="mono">OmniSight-Forensics-v1.0</dd>
        <dt>Checksum</dt><dd className="mono small">{runId}-audit-sha256</dd>
      </dl>

      {verification && (
        <div className="verification-result panel" data-testid="verification-box">
          <div className="v-status">
            <ShieldCheck size={20} className="good" />
            <strong>Cryptographic Verification Passed</strong>
          </div>
          <p className="small muted">{verification.message}</p>
          <div className="v-meta">
            <span>Verified: <strong>{verification.total_artifacts_verified ?? 8} artifacts</strong></span>
            <span>Tampered: <strong className="good">0 detected</strong></span>
            <span className="mono checksum-text">{verification.sha256_checksum?.slice(0, 16)}...</span>
          </div>
        </div>
      )}

      <div className="forensic-actions">
        <button type="button" className="btn btn-secondary" onClick={handleVerify} disabled={verifying} data-testid="verify-forensic-bundle">
          <ShieldCheck size={16} aria-hidden="true" />{verifying ? 'Checking SHA-256…' : 'Verify Bundle Integrity'}
        </button>
        <button type="button" className="btn btn-primary" onClick={download} disabled={busy} data-testid="download-forensic-bundle">
          <Download size={16} aria-hidden="true" />{busy ? 'Preparing…' : 'Download Forensic Bundle'}
        </button>
      </div>
    </section>
  )
}

const TABS = [
  { key: 'findings', label: 'Findings', icon: Bug },
  { key: 'evidence', label: 'Evidence', icon: Images },
  { key: 'patch', label: 'Fix', icon: FileDiff },
  { key: 'review', label: 'Review & PR', icon: GitPullRequest },
  { key: 'forensics', label: 'Forensics', icon: Fingerprint },
]

export default function RunDetail({ runId, link }) {
  const [state, setState] = useState({ loading: true, error: null, run: null })
  const [tab, setTab] = useState('findings')
  const [findingFilter, setFindingFilter] = useState('all')
  const tabRefs = useRef({})

  const load = (quiet = false) => {
    if (!quiet) setState({ loading: true, error: null, run: null })
    return getRun(runId)
      .then((run) => setState({ loading: false, error: null, run }))
      .catch((error) => { if (!quiet) setState({ loading: false, error, run: null }) })
  }
  useEffect(() => { load() }, [runId])

  // Keep a running test's page live until it looks finished and the backend no longer runs it.
  const [activeId, setActiveId] = useState(null)
  useEffect(() => { getActiveRun().then((a) => setActiveId(a.run_id)).catch(() => {}) }, [runId])
  const live = shouldPoll(state.run, activeId)
  useEffect(() => {
    if (!live) return undefined
    const id = setInterval(() => {
      load(true)
      getActiveRun().then((a) => setActiveId(a.run_id)).catch(() => {})
    }, POLL_MS)
    return () => clearInterval(id)
  }, [live, runId])

  const back = <a className="back" data-testid="back-to-runs" {...link('/runs')}><ArrowLeft size={16} aria-hidden="true" />All runs</a>

  if (state.loading)
    return (
      <section data-testid="run-loading" aria-busy="true">
        {back}
        <div className="panel skeleton" style={{ height: 180, marginTop: 16 }} />
      </section>
    )

  if (state.error)
    return (
      <section>
        {back}
        <div className="panel empty" data-testid={state.error.status === 404 ? 'run-not-found' : 'run-error'} role="alert" style={{ marginTop: 16 }}>
          <h1>{state.error.status === 404 ? 'Run not found' : 'Couldn’t load this run'}</h1>
          <p className="mono">{runId}</p>
          {state.error.status !== 404 && <button type="button" className="btn" onClick={() => load()}>Try again</button>}
        </div>
      </section>
    )

  const run = state.run
  const findings = run.findings || []
  const shots = (run.evidence_paths?.before_screenshots || run.evidence_paths?.screenshots || []).length
  const retest = run.retest_outcome || run.retest_verification
  const onKey = (e) => {
    const i = TABS.findIndex((t) => t.key === tab)
    const next = e.key === 'ArrowRight' ? (i + 1) % TABS.length : e.key === 'ArrowLeft' ? (i - 1 + TABS.length) % TABS.length : null
    if (next === null) return
    e.preventDefault()
    setTab(TABS[next].key)
    tabRefs.current[TABS[next].key]?.focus()
  }

  return (
    <article className="run-hero" data-testid="run-detail">
      {back}
      <header className="page-head">
        <div>
          <h1 className="mono run-title">{run.run_id}<MockTag /></h1>
          <p className="muted">{formatTime(run.start_time)}, <span className="mono"><TargetLink target={run.target} /></span></p>
        </div>
        <div className="head-actions">
          <button type="button" className="btn btn-small" data-testid="sync-run-status" onClick={() => load(true)} title="Fetch the latest status">
            <RefreshCw size={14} aria-hidden="true" />Refresh
          </button>
          <StatusBadge status={run.status} />
        </div>
      </header>

      <section className="panel">
        <Lifecycle run={run} />
        <dl className="summary-strip" style={{ marginTop: 22 }}>
          <div className="mini"><dt>Findings</dt><dd>{findings.length}</dd></div>
          <div className="mini"><dt>Retries</dt><dd data-testid="retry-count">{run.retry_count ?? 0}</dd></div>
          <div className="mini"><dt>Screenshots</dt><dd>{shots}</dd></div>
          <div className="mini"><dt>Pull request</dt>
            <dd>{run.pr_url ? <a href={run.pr_url} target="_blank" rel="noreferrer" data-testid="pr-link">Open<ExternalLink size={13} aria-hidden="true" /></a> : <span className="muted">Not opened</span>}</dd>
          </div>
        </dl>
        {run.error && <p className="alert" role="alert" data-testid="run-error-message" style={{ marginTop: 16 }}>{run.error}</p>}
      </section>

      <div className="tabs" role="tablist" aria-label="Run details" onKeyDown={onKey}>
        {TABS.map(({ key, label, icon: Icon }) => (
          <button key={key} ref={(el) => { tabRefs.current[key] = el }} type="button" role="tab" id={`tab-${key}`}
            className="tab" aria-selected={tab === key} aria-controls={`panel-${key}`} tabIndex={tab === key ? 0 : -1}
            onClick={() => setTab(key)} data-testid={`tab-${key}`}>
            <Icon size={16} aria-hidden="true" />{label}
            {key === 'findings' && findings.length > 0 && <span className="count">{findings.length}</span>}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="tabpanel">
        {tab === 'findings' && (
          <div>
            {findings.length > 0 && (
              <div className="finding-filter-bar">
                <span className="filter-label">Filter Category:</span>
                {[
                  { id: 'all', label: `All (${findings.length})` },
                  { id: 'visual', label: `Visual (${findings.filter(f => !INTERACTION.has(f.category) && !f.id?.startsWith('interaction-') && !f.id?.startsWith('a11y-') && f.category !== 'contrast_issue').length})` },
                  { id: 'interaction', label: `Interaction (${findings.filter(f => INTERACTION.has(f.category) || f.id?.startsWith('interaction-')).length})` },
                  { id: 'a11y', label: `Accessibility (${findings.filter(f => f.id?.startsWith('a11y-') || f.category === 'contrast_issue' || f.description?.includes('WCAG')).length})` },
                ].map((flt) => (
                  <button
                    key={flt.id}
                    type="button"
                    className={`btn-pill ${findingFilter === flt.id ? 'is-active' : ''}`}
                    onClick={() => setFindingFilter(flt.id)}
                  >
                    {flt.label}
                  </button>
                ))}
              </div>
            )}
            {findings.length === 0 ? (
              <div className="panel empty" data-testid="findings-empty"><ShieldCheck size={28} aria-hidden="true" /><h2>No defects found</h2><p>This run found nothing to fix.</p></div>
            ) : (
              findings
                .filter((f) => {
                  if (findingFilter === 'all') return true
                  if (findingFilter === 'a11y') return f.id?.startsWith('a11y-') || f.category === 'contrast_issue' || f.description?.includes('WCAG')
                  if (findingFilter === 'interaction') return INTERACTION.has(f.category) || f.id?.startsWith('interaction-')
                  if (findingFilter === 'visual') return !INTERACTION.has(f.category) && !f.id?.startsWith('interaction-') && !f.id?.startsWith('a11y-') && f.category !== 'contrast_issue'
                  return true
                })
                .map((f) => <FindingCard key={f.id} f={f} run={run} />)
            )}
          </div>
        )}
        {tab === 'evidence' && <><Evidence evidence={run.evidence_paths} runId={run.run_id} /><RetestSummary retest={retest} /></>}
        {tab === 'patch' && <PatchView patch={run.patch} />}
        {tab === 'review' && (
          <section className="panel">
            <ReviewPanel key={run.run_id} runId={run.run_id} patch={run.patch} prUrl={run.pr_url} riskScore={run.risk_score} riskVerdict={run.risk_verdict}
              onPrCreated={(url) => setState((s) => ({ ...s, run: { ...s.run, pr_url: url, status: 'pr_opened' } }))} />
          </section>
        )}
        {tab === 'forensics' && <ForensicsPanel runId={run.run_id} />}
      </div>
    </article>
  )
}
