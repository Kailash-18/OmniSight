import { useEffect, useState } from 'react'
import { GitPullRequest, LoaderCircle, ExternalLink, CircleCheck } from 'lucide-react'
import { loadReview, saveReview } from '../review.js'
import { createPullRequest, getPrChecks } from '../api.js'
import { ciMeta } from '../lifecycle.js'

const CI_POLL_MS = 15000

// Live CI result for the PR, re-checked while GitHub is still running the checks.
function CiStatus({ runId, prUrl }) {
  const [checks, setChecks] = useState(null)
  useEffect(() => {
    let stop = false
    let timer
    const load = () => getPrChecks(runId)
      .then((c) => {
        if (stop) return
        setChecks(c)
        if (ciMeta(c).poll) timer = setTimeout(load, CI_POLL_MS)
      })
      .catch(() => { if (!stop) setChecks({ state: 'unavailable' }) })
    load()
    return () => { stop = true; clearTimeout(timer) }
  }, [runId, prUrl])
  if (!checks) return <span className="pill tone-neutral" data-testid="ci-status"><LoaderCircle className="spin" size={13} aria-hidden="true" />Checking CI…</span>
  const meta = ciMeta(checks)
  return (
    <span className="ci-row" data-testid="ci-status">
      <span className={`pill tone-${meta.tone}${meta.poll ? ' live' : ''}`}><span className="dot" aria-hidden="true" />{meta.label}</span>
      {meta.detail && <span className="muted small">{meta.detail}</span>}
    </span>
  )
}

export default function ReviewPanel({ runId, patch, prUrl: initialPrUrl, riskScore, riskVerdict, onPrCreated }) {
  const [review, setReview] = useState(() => loadReview(runId))
  const [note, setNote] = useState(review?.note || '')
  const [persisted, setPersisted] = useState(true)
  const [prUrl, setPrUrl] = useState(initialPrUrl)
  const [creatingPr, setCreatingPr] = useState(false)
  const [prError, setPrError] = useState(null)

  if (!patch) return <p className="muted" data-testid="review-unavailable">This run has no proposed fix to review.</p>
  // A validator-rejected patch can never be applied, so there's nothing for a human to approve.
  if (patch.validation_status === false)
    return <p className="muted" data-testid="review-unavailable">The safety check rejected this fix, so there’s nothing to approve.</p>

  const decide = (decision) => {
    const next = { decision, note: note.trim(), decided_at: new Date().toISOString() }
    setReview(next)
    setPersisted(saveReview(runId, next))
  }

  const handleCreatePr = async () => {
    setCreatingPr(true)
    setPrError(null)
    try {
      const res = await createPullRequest(runId)
      if (res.pr_url) {
        setPrUrl(res.pr_url)
        onPrCreated?.(res.pr_url)
      }
    } catch (err) {
      setPrError(err.message || 'Couldn’t open the pull request')
    } finally {
      setCreatingPr(false)
    }
  }

  return (
    <div className="review" data-testid="review-panel">
      {riskScore != null && (
        <div className={`risk-gate-banner risk-${riskVerdict || 'review'}`}>
          <div className="risk-score-badge">
            <span className="risk-num">{riskScore}</span>
            <span className="risk-denom">/ 100</span>
          </div>
          <div className="risk-details">
            <strong>{riskVerdict === 'auto_approved' ? '✓ Auto-Merge Safety Approved' : '⚠ Manual Human Review Required'}</strong>
            <p className="muted small">
              {riskVerdict === 'auto_approved'
                ? 'Remediation evaluated as low blast-radius with high visual confidence score.'
                : 'Remediation affects sensitive layout containers; manual code verification recommended before merge.'}
            </p>
          </div>
        </div>
      )}
      <p className="muted small">Approve or reject the fix here (saved in this browser), then open a pull request on GitHub.</p>
      {review && (
        <p className={`review-result ${review.decision}`} data-testid="review-result" role="status">
          {review.decision === 'approved' ? 'Approved' : 'Rejected'}
          {review.note ? `: “${review.note}”` : ''}
          {!persisted && <span className="muted small"> (couldn’t save, browser storage is blocked)</span>}
        </p>
      )}
      <label className="field">Reviewer note (optional)
        <textarea className="input" rows="2" value={note} onChange={(e) => setNote(e.target.value)} data-testid="review-note" />
      </label>
      <div className="review-actions">
        <button type="button" className="btn btn-good" data-testid="review-approve" aria-pressed={review?.decision === 'approved'} onClick={() => decide('approved')}>Approve fix</button>
        <button type="button" className="btn btn-bad" data-testid="review-reject" aria-pressed={review?.decision === 'rejected'} onClick={() => decide('rejected')}>Reject fix</button>
        {!prUrl && (
          <button type="button" className="btn btn-primary" data-testid="review-create-pr" disabled={creatingPr} onClick={handleCreatePr}>
            {creatingPr ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> : <GitPullRequest size={16} aria-hidden="true" />}
            {creatingPr ? 'Opening pull request…' : 'Open pull request'}
          </button>
        )}
      </div>
      {prError && <p className="alert" role="alert" data-testid="pr-create-error">{prError}</p>}
      {prUrl && (
        <div className="pr-banner" data-testid="pr-active-banner">
          <strong><CircleCheck size={18} aria-hidden="true" />Pull request opened</strong>
          <CiStatus runId={runId} prUrl={prUrl} />
          <div className="pr-banner-links">
            <a href={prUrl} target="_blank" rel="noreferrer" className="pr-banner-link" data-testid="review-pr-link">{prUrl}<ExternalLink size={13} aria-hidden="true" /></a>
            <a href={`${prUrl}/checks`} target="_blank" rel="noreferrer" data-testid="review-ci-link">View CI on GitHub<ExternalLink size={13} aria-hidden="true" /></a>
          </div>
        </div>
      )}
    </div>
  )
}
