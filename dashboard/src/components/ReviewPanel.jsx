import { useState } from 'react'
import { loadReview, saveReview } from '../review.js'
import { createPullRequest } from '../api.js'

export default function ReviewPanel({ runId, patch, prUrl: initialPrUrl, onPrCreated }) {
  const [review, setReview] = useState(() => loadReview(runId))
  const [note, setNote] = useState(review?.note || '')
  const [persisted, setPersisted] = useState(true)
  const [prUrl, setPrUrl] = useState(initialPrUrl)
  const [creatingPr, setCreatingPr] = useState(false)
  const [prError, setPrError] = useState(null)

  if (!patch) return <p className="muted" data-testid="review-unavailable">No proposed fix to review for this run.</p>
  // A validator-rejected patch can never be applied, so there's nothing for a human to approve.
  if (patch.validation_status === false)
    return <p className="muted" data-testid="review-unavailable">The validator rejected this patch, so there's nothing to approve.</p>

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
      setPrError(err.message || 'Failed to open Pull Request')
    } finally {
      setCreatingPr(false)
    }
  }

  return (
    <div className="review" data-testid="review-panel">
      <p className="muted small">Human-in-the-loop QA review controls. Approve patches locally or open automated remediation Pull Requests directly on GitHub.</p>
      {review && (
        <p className={`review-result ${review.decision}`} data-testid="review-result" role="status">
          {review.decision === 'approved' ? 'Approved' : 'Rejected'}
          {review.note ? ` — “${review.note}”` : ''}
          {!persisted && <span className="muted small"> (couldn't save; storage blocked)</span>}
        </p>
      )}
      <label className="field">
        <span>Reviewer note (optional)</span>
        <textarea rows="2" value={note} onChange={(e) => setNote(e.target.value)} data-testid="review-note" />
      </label>
      <div className="review-actions">
        <button type="button" className="btn btn-good" data-testid="review-approve" aria-pressed={review?.decision === 'approved'} onClick={() => decide('approved')}>Approve fix</button>
        <button type="button" className="btn btn-bad" data-testid="review-reject" aria-pressed={review?.decision === 'rejected'} onClick={() => decide('rejected')}>Reject fix</button>
        {!prUrl && (
          <button
            type="button"
            className="btn btn-primary"
            data-testid="review-create-pr"
            disabled={creatingPr}
            onClick={handleCreatePr}
          >
            {creatingPr ? 'Opening Pull Request…' : '🚀 Open Pull Request'}
          </button>
        )}
      </div>

      {prError && (
        <p className="alert" role="alert" data-testid="pr-create-error">
          {prError}
        </p>
      )}

      {prUrl && (
        <div className="pr-banner" data-testid="pr-active-banner">
          <span>Pull Request Active</span>
          <a href={prUrl} target="_blank" rel="noreferrer" className="pr-banner-link" data-testid="review-pr-link">
            {prUrl} ↗
          </a>
        </div>
      )}
    </div>
  )
}
