import { useEffect, useState } from 'react'
import { getRun } from '../api.js'
import { formatConfidence, formatTime, diffLines, validatorErrors, defectPage } from '../format.js'
import StatusBadge from './StatusBadge.jsx'
import MockTag from './MockTag.jsx'
import TargetLink from './TargetLink.jsx'

// "Open the store, then do these steps at this viewport" so a reviewer can see the defect live.
function DefectLink({ link, id }) {
  if (!link) return <span className="muted">Not available (no screenshot or no valid target URL)</span>
  return (
    <div className="defect-link" data-testid={`defect-link-${id}`}>
      <a href={link.url} target="_blank" rel="noreferrer" className="btn btn-small">
        {link.page ? `Open ${link.page} page` : 'Open store'} ↗<span className="visually-hidden"> (opens the store in a new tab)</span>
      </a>
      <ol className="defect-steps small muted" data-testid="defect-steps">
        {link.size && <li>Set the browser to {link.size} (DevTools device mode)</li>}
        {link.page && link.steps.map((s) => <li key={s}>{s}</li>)}
        {link.page === 'Products' && <li>The defect is visible on load</li>}
        {!link.page && <li>Page not identified from the evidence; compare with the screenshots below</li>}
      </ol>
    </div>
  )
}
import Evidence from './Evidence.jsx'
import ReviewPanel from './ReviewPanel.jsx'

export default function RunDetail({ runId, link }) {
  const [state, setState] = useState({ loading: true, error: null, run: null })

  const load = () => {
    setState({ loading: true, error: null, run: null })
    getRun(runId)
      .then((run) => setState({ loading: false, error: null, run }))
      .catch((error) => setState({ loading: false, error, run: null }))
  }
  useEffect(load, [runId])

  const back = <a className="back" data-testid="back-to-runs" {...link('/')}>← All runs</a>

  if (state.loading) return <section className="panel state" data-testid="run-loading" aria-busy="true">Loading run…</section>

  if (state.error)
    return (
      <section>
        {back}
        <div className="panel state state-error" data-testid={state.error.status === 404 ? 'run-not-found' : 'run-error'} role="alert">
          <h1>{state.error.status === 404 ? 'Run not found' : "Couldn't load this run"}</h1>
          <p className="mono">{runId}</p>
          {state.error.status !== 404 && <button type="button" className="btn" onClick={load}>Retry</button>}
        </div>
      </section>
    )

  const run = state.run
  const findings = run.findings || []
  const patch = run.patch
  const errors = validatorErrors(patch)
  const retest = run.retest_verification

  return (
    <article data-testid="run-detail">
      {back}
      <div className="page-head">
        <div>
          <h1 className="mono run-title">{run.run_id} <MockTag /></h1>
          <p className="muted">{formatTime(run.start_time)} · <span className="mono"><TargetLink target={run.target} /></span></p>
        </div>
        <StatusBadge status={run.status} />
      </div>

      <section className="panel" aria-labelledby="h-summary">
        <h2 id="h-summary">Summary</h2>
        <dl className="facts">
          <dt>Retries</dt><dd data-testid="retry-count">{run.retry_count ?? 0}</dd>
          <dt>Issues</dt><dd>{findings.length}</dd>
          <dt>Pull request</dt>
          <dd>{run.pr_url ? <a href={run.pr_url} target="_blank" rel="noreferrer" data-testid="pr-link">{run.pr_url}</a> : <span className="muted">Not opened</span>}</dd>
          <dt>Steps</dt>
          <dd>{run.steps?.length ? <ol className="steps">{run.steps.map((s, i) => <li key={i} className="mono">{s}</li>)}</ol> : <span className="muted">None completed</span>}</dd>
        </dl>
        {run.error && <p className="alert" role="alert" data-testid="run-error-message">{run.error}</p>}
      </section>

      <section className="panel" aria-labelledby="h-findings">
        <h2 id="h-findings">Findings</h2>
        {findings.length === 0 ? (
          <p className="muted" data-testid="findings-empty">No visual defects reported.</p>
        ) : (
          findings.map((f) => (
            <div key={f.id} className="finding" data-testid={`finding-${f.id}`}>
              <div className="finding-head">
                <strong>{f.description}</strong>
                <span className={`sev sev-${f.severity}`}>{f.severity}</span>
              </div>
              <dl className="facts compact">
                <dt>Category</dt><dd className="mono">{f.category}</dd>
                <dt>Viewport</dt><dd className="mono">{f.viewport}</dd>
                {f.target_element && <><dt>Element</dt><dd className="mono">{f.target_element}</dd></>}
                <dt>Confidence</dt>
                <dd>
                  <span className="conf" aria-hidden="true"><span style={{ width: formatConfidence(f.confidence) === '—' ? 0 : formatConfidence(f.confidence) }} /></span>
                  <span data-testid="confidence">{formatConfidence(f.confidence)}</span>
                </dd>
                <dt>Status</dt><dd className="mono">{f.status}</dd>
                <dt>Suggested fix</dt><dd>{f.suggested_change}</dd>
                <dt>Rationale</dt><dd>{f.rationale}</dd>
                <dt>Defect page</dt><dd><DefectLink link={defectPage(run.target, f, run.evidence_paths)} id={f.id} /></dd>
              </dl>
            </div>
          ))
        )}
      </section>

      <section className="panel" aria-labelledby="h-evidence">
        <h2 id="h-evidence">Evidence: before / after</h2>
        <Evidence evidence={run.evidence_paths} />
        {typeof retest?.mismatch_percentage === 'number' && (
          <p className="muted small">Pixel mismatch after retest: {retest.mismatch_percentage.toFixed(2)}%</p>
        )}
      </section>

      <section className="panel" aria-labelledby="h-patch">
        <h2 id="h-patch">Proposed patch</h2>
        {!patch ? (
          <p className="muted" data-testid="patch-empty">No patch was proposed.</p>
        ) : (
          <>
            <p>
              <span className="mono">{patch.target_file}</span>{' '}
              {patch.validation_status === true && <span className="badge tone-good" data-testid="patch-valid">Passed validation</span>}
              {patch.validation_status === false && <span className="badge tone-bad" data-testid="patch-invalid">Rejected by validator</span>}
            </p>
            {errors.length > 0 && (
              <ul className="alert" data-testid="validator-errors">{errors.map((e) => <li key={e}>{e}</li>)}</ul>
            )}
            <pre className="diff" data-testid="patch-diff">
              {diffLines(patch.diff).map((l, i) => <span key={i} className={`dl dl-${l.kind}`}>{l.line}{'\n'}</span>)}
            </pre>
          </>
        )}
      </section>

      <section className="panel" aria-labelledby="h-review">
        <h2 id="h-review">Review</h2>
        <ReviewPanel key={run.run_id} runId={run.run_id} patch={patch} />
      </section>
    </article>
  )
}
