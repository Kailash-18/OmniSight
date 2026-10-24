// Pure display helpers for run data (docs/api-contract.md). No React here, so node:test can cover it.

// Run status enum: must match backend + automation exactly.
export const STATUSES = {
  queued: { label: 'Queued', tone: 'neutral' },
  running: { label: 'Running', tone: 'info' },
  audited: { label: 'Audited', tone: 'info' },
  patch_rejected: { label: 'Patch rejected', tone: 'bad' },
  verifying: { label: 'Verifying', tone: 'info' },
  fixed: { label: 'Fixed', tone: 'good' },
  needs_review: { label: 'Needs review', tone: 'warn' },
  pr_opened: { label: 'PR opened', tone: 'good' },
  failed: { label: 'Failed', tone: 'bad' },
}

// Unknown values still render instead of crashing, so a new backend status is visible, not hidden.
export const statusMeta = (status) => STATUSES[status] || { label: status ? String(status) : 'Unknown', tone: 'neutral' }

export const formatConfidence = (c) =>
  typeof c === 'number' && c >= 0 && c <= 1 ? `${Math.round(c * 100)}%` : '—'

// UTC so the same run renders identically for every reviewer.
export const formatTime = (iso) => {
  const d = new Date(iso)
  if (!iso || Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }) + ' UTC'
}

// "artifacts/runs/r1/retest/desktop_1280x800_checkout_after.png" -> { key, viewport, page }
// Accepts the runner's "_after"/"_diff"/"_annotated" suffix and the contract's "retest_" prefix.
export function parseShot(path) {
  const name = String(path).split('/').pop().replace(/\.png$/i, '')
    .replace(/^retest_/, '')
    .replace(/_(after|diff|annotated)$/, '')
  const m = name.match(/^((?:desktop|mobile)_\d+x\d+)_(.+)$/)
  return m ? { key: name, viewport: m[1], page: m[2] } : { key: name, viewport: null, page: name }
}

// Pair before/after screenshots by viewport + page. Unmatched sides stay null.
export function pairEvidence(evidence) {
  const pairs = new Map()
  for (const p of evidence?.before_screenshots || []) {
    pairs.set(parseShot(p).key, { ...parseShot(p), before: p, after: null })
  }
  for (const p of evidence?.after_screenshots || []) {
    const shot = parseShot(p)
    pairs.set(shot.key, { ...(pairs.get(shot.key) || { ...shot, before: null }), after: p })
  }
  return [...pairs.values()]
}

// Fixture paths live in public/ ("fixtures/x.png"); live paths are served by the dev server at /artifacts/.
// The runner records absolute paths (/Users/.../OmniSight/artifacts/runs/...), so keep only the artifacts/ part.
export const evidenceUrl = (path) => {
  if (!path) return null
  const p = String(path).replace(/\\/g, '/')
  const i = p.lastIndexOf('/artifacts/')
  return i >= 0 ? p.slice(i) : '/' + p.replace(/^\/+/, '')
}

// target comes from the backend: only ever link http(s), never javascript: or other schemes.
export function safeUrl(target) {
  try {
    const url = new URL(target)
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null
  } catch {
    return null
  }
}

const PAGES = { home: 'Products', cart: 'Cart', checkout: 'Checkout' }

// Where a finding shows up in the store. The page comes from its evidence screenshot
// (same viewport, else the first one). Cart and checkout need items first and the store's cart is
// in memory, so a deep link would open empty: those link to the store home with steps instead.
export function defectPage(target, finding, evidence) {
  const base = safeUrl(target)
  const pairs = pairEvidence(evidence)
  const pair = pairs.find((p) => p.viewport === finding?.viewport) || pairs[0]
  if (!base || !pair) return null
  const viewport = pair.viewport || finding?.viewport
  const size = viewport?.match(/(\d+)x(\d+)$/)
  const steps = {
    home: [],
    cart: ['Add any product', 'Open Cart'],
    checkout: ['Add any product', 'Open Cart', 'Continue to checkout'],
  }[pair.page] || []
  return {
    url: base, // store home; every journey starts here
    page: PAGES[pair.page] || pair.page,
    viewport,
    size: size ? `${size[1]}×${size[2]}` : null,
    steps,
  }
}

// Detail -> the GET /runs summary shape.
export const toSummary = (run) => ({
  run_id: run.run_id,
  start_time: run.start_time,
  target: run.target,
  status: run.status,
  issue_count: run.issue_count ?? run.findings?.length ?? 0,
  pr_url: run.pr_url ?? null,
})

export const diffLines = (diff) =>
  String(diff || '').split('\n').map((line) => ({
    line,
    kind: line.startsWith('+') ? 'add' : line.startsWith('-') ? 'del' : 'ctx',
  }))

// Contract allows validator_errors as null, a string, or a list.
export const validatorErrors = (patch) => {
  const e = patch?.validator_errors
  if (!e) return []
  return Array.isArray(e) ? e.map(String) : [String(e)]
}
