import { useState } from 'react'
import { loadReview, saveReview } from '../review.js'

export default function ReviewPanel({ runId, patch }) {
  const [review, setReview] = useState(() => loadReview(runId))
  const [note, setNote] = useState(review?.note || '')
  const [persisted, setPersisted] = useState(true)

  if (!patch) return <p className="muted" data-testid="review-unavailable">No proposed fix to review for this run.</p>
  // A validator-rejected patch can never be applied, so there's nothing for a human to approve.
  if (patch.validation_status === false)
    return <p className="muted" data-testid="review-unavailable">The validator rejected this patch, so there's nothing to approve.</p>

  const decide = (decision) => {
    const next = { decision, note: note.trim(), decided_at: new Date().toISOString() }
    setReview(next)
    setPersisted(saveReview(runId, next))
  }

  return (
    <div className="review" data-testid="review-panel">
      <p className="muted small">Local review state, saved in this browser only. It does not approve or merge anything on GitHub.</p>
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
      </div>
    </div>
  )
}
