// Reviewer approve/reject decisions. The backend has no review endpoint yet, so this is
// per-browser local state only; it is labelled as such in the UI and never touches GitHub.
const key = (runId) => `omnisight.review.${runId}`

export function loadReview(runId) {
  try {
    const saved = JSON.parse(localStorage.getItem(key(runId)))
    return saved?.decision === 'approved' || saved?.decision === 'rejected' ? saved : null
  } catch {
    return null
  }
}

export function saveReview(runId, review) {
  try {
    localStorage.setItem(key(runId), JSON.stringify(review))
    return true
  } catch {
    return false // storage blocked (private mode etc.); caller keeps it in memory
  }
}
