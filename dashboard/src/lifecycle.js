// Pure run helpers for the overview tiles, live card and lifecycle tracker.
export const STEPS = [
  { key: 'queued', label: 'Queued' },
  { key: 'running', label: 'Testing' },
  { key: 'audited', label: 'Audited' },
  { key: 'verifying', label: 'Verifying fix' },
  { key: 'fixed', label: 'Fixed' },
  { key: 'pr_opened', label: 'PR opened' },
]
const ORDER = { queued: 0, running: 1, audited: 2, verifying: 3, fixed: 4, needs_review: 4, pr_opened: 5 }
const ACTIVE = new Set(['queued', 'running', 'verifying'])
export const isActiveStatus = (s) => ACTIVE.has(s)

export function lifecycle(run) {
  const s = run?.status
  if (s === 'failed') {
    const failAt = run?.patch || run?.retest_outcome ? 3 : 1
    return STEPS.map((st, i) => ({ ...st, state: i < failAt ? 'done' : i === failAt ? 'failed' : 'todo' }))
  }
  if (s === 'patch_rejected') return STEPS.map((st, i) => ({ ...st, state: i < 3 ? 'done' : i === 3 ? 'failed' : 'todo' }))
  const at = ORDER[s] ?? 0
  // Only when the run is known to have had nothing to fix (summary rows don't carry patch/findings).
  const noFix = s === 'fixed' && run?.patch === null && Array.isArray(run?.findings) && run.findings.length === 0
  return STEPS.map((st, i) => {
    if (noFix && st.key === 'verifying') return { ...st, state: 'skipped' }
    if (s === 'needs_review' && st.key === 'fixed') return { ...st, label: 'Needs review', state: 'current' }
    const finished = s === 'fixed' || s === 'pr_opened'
    const state = i < at || (i === at && finished) ? 'done' : i === at ? 'current' : 'todo'
    return { ...st, state }
  })
}

export function stats(runs) {
  const finished = runs.filter((r) => !isActiveStatus(r.status))
  const fixed = runs.filter((r) => r.status === 'fixed' || r.status === 'pr_opened').length
  return {
    total: runs.length,
    bugs: runs.reduce((n, r) => n + (Number(r.issue_count) || 0), 0),
    fixRate: finished.length ? `${Math.round((fixed / finished.length) * 100)}%` : '—',
    prs: runs.filter((r) => r.pr_url).length,
  }
}

export const clampPercent = (n) => (Number.isFinite(n) ? Math.min(100, Math.max(0, n)) : 50)

export function relativeTime(iso, now = Date.now()) {
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return '—'
  const s = Math.max(0, Math.round((now - t) / 1000))
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}

// A run page keeps refreshing while the run looks in progress OR the backend still has it as the
// active launched run (it passes through "audited" before the interaction check and fix check).
export const shouldPoll = (run, activeRunId) => !!run && (isActiveStatus(run.status) || activeRunId === run.run_id)

// CI result of a run's pull request (GET /runs/{id}/checks) -> pill text, tone, and whether to re-check.
export function ciMeta(checks) {
  const c = checks || {}
  switch (c.state) {
    case 'passed': return { label: 'CI passed', tone: 'good', detail: `${c.passed} of ${c.total} checks passed`, poll: false }
    case 'failed': return { label: 'CI failed', tone: 'bad', detail: `${c.failed} of ${c.total} checks failed`, poll: false }
    case 'running': return { label: 'CI running', tone: 'info', detail: `${c.running} of ${c.total} checks still running`, poll: true }
    case 'pending': return { label: 'CI starting', tone: 'info', detail: 'Waiting for GitHub to start the checks', poll: true }
    case 'unavailable': return { label: 'CI status unavailable', tone: 'neutral', detail: 'The backend has no GitHub token, or GitHub didn’t answer', poll: false }
    default: return { label: 'CI status unknown', tone: 'neutral', detail: '', poll: false }
  }
}
