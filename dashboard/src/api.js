// Live backend (default) through the Vite /api proxy, or fixtures with VITE_DATA_SOURCE=mock.
import fixtureRuns from './fixtures/runs.json'
import { toSummary } from './format.js'
import { authHeaders, checkResponse, getToken, setSession } from './auth.js'

export const DATA_SOURCE = import.meta.env.VITE_DATA_SOURCE === 'mock' ? 'mock' : 'live'

async function call(path, { method = 'GET', body } = {}) {
  const res = await fetch('/api' + path, {
    method,
    headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), ...authHeaders(getToken()) },
    body: body ? JSON.stringify(body) : undefined,
  })
  await checkResponse(res)
  return res.status === 204 ? null : res.json()
}

export async function login(username, password) {
  const session = await call('/auth/login', { method: 'POST', body: { username, password } })
  setSession(session)
  return session
}

export const me = () => call('/auth/me')

export async function listRuns() {
  const runs = DATA_SOURCE === 'mock' ? fixtureRuns : await call('/runs')
  return runs.map(toSummary)
}

export async function getRun(runId) {
  if (DATA_SOURCE === 'live') return call(`/runs/${encodeURIComponent(runId)}`)
  const run = fixtureRuns.find((r) => r.run_id === runId)
  if (!run) throw Object.assign(new Error('Run not found'), { status: 404 })
  return run
}

export function startRun(targetUrl, { retest = true } = {}) {
  if (DATA_SOURCE === 'mock') return Promise.reject(Object.assign(new Error('Runs can only be started in live mode'), { status: 400 }))
  return call('/runs', { method: 'POST', body: { target_url: targetUrl.trim(), launch: true, retest } })
}

export async function getActiveRun() {
  if (DATA_SOURCE === 'mock') return { run_id: null }
  return call('/runs/active')
}

export async function createPullRequest(runId, payload = {}) {
  if (DATA_SOURCE === 'mock') {
    const prNumber = Math.abs(runId.split('').reduce((a, b) => (a << 5) - a + b.charCodeAt(0), 0)) % 1000 + 10
    const prUrl = `https://github.com/Kailash-18/OmniSight/pull/${prNumber}`
    const run = fixtureRuns.find((r) => r.run_id === runId)
    if (run) { run.pr_url = prUrl; run.status = 'pr_opened' }
    return { status: 'success', run_id: runId, pr_url: prUrl, message: 'Pull Request created successfully.' }
  }
  return call(`/runs/${encodeURIComponent(runId)}/create-pr`, { method: 'POST', body: payload })
}

export async function getForensicBundle(runId) {
  if (DATA_SOURCE === 'mock') {
    return {
      run_id: runId, bundle_name: `forensic_bundle_${runId}.zip`,
      sha256_checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', artifact_count: 8, size_bytes: 42100,
    }
  }
  return call(`/runs/${encodeURIComponent(runId)}/forensics`)
}

// CI result of the run's pull request; the backend reads GitHub with its own token.
export async function getPrChecks(runId) {
  if (DATA_SOURCE === 'mock') {
    const run = fixtureRuns.find((r) => r.run_id === runId)
    return run?.pr_url ? { state: 'passed', total: 4, passed: 4, failed: 0, running: 0, checks_url: `${run.pr_url}/checks` } : { state: 'none' }
  }
  return call(`/runs/${encodeURIComponent(runId)}/checks`)
}

// A plain <a href> can't send the bearer token, so fetch the zip and hand the browser a blob URL.
export async function downloadForensicBundle(runId) {
  if (DATA_SOURCE === 'mock') throw Object.assign(new Error('Forensic bundles are only available in live mode'), { status: 400 })
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/forensics/download`, { headers: authHeaders(getToken()) })
  await checkResponse(res)
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: `forensic_bundle_${runId}.zip` })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// Aggregates from Kailash's GET /runs/metrics/summary (defect categories, average pixel-diff reduction).
export async function fetchMetricsSummary() {
  if (DATA_SOURCE === 'mock') {
    const cats = {}
    for (const r of fixtureRuns) for (const f of r.findings || []) cats[f.category] = (cats[f.category] || 0) + 1
    return {
      total_runs: fixtureRuns.length,
      fixed_runs: fixtureRuns.filter((r) => r.status === 'fixed' || r.status === 'pr_opened').length,
      needs_review_runs: fixtureRuns.filter((r) => r.status === 'needs_review').length,
      failed_runs: fixtureRuns.filter((r) => r.status === 'failed').length,
      success_rate_percentage: 0,
      defect_categories: cats,
      average_diff_reduction: 0,
    }
  }
  return call('/runs/metrics/summary')
}

export async function fetchTargetHosts() {
  if (DATA_SOURCE === 'mock') {
    return {
      allowed_hosts: ['localhost', '127.0.0.1', 'staging.internal', '*.flipkart.com', 'flipkart.com', '*'],
      wildcard_enabled: true,
    }
  }
  return call('/config/target-hosts')
}

export async function verifyForensicBundle(runId) {
  if (DATA_SOURCE === 'mock') {
    return {
      run_id: runId,
      status: 'verified',
      verified: true,
      sha256_checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      total_artifacts_verified: 8,
      tampered_artifacts: 0,
      message: 'Cryptographic SHA-256 integrity verified. No artifacts modified.',
    }
  }
  return call(`/runs/${encodeURIComponent(runId)}/verify-bundle`)
}

export async function downloadReportMarkdown(runId) {
  if (DATA_SOURCE === 'mock') {
    const run = fixtureRuns.find((r) => r.run_id === runId) || {}
    const content = `# OmniSight Visual QA Audit Report\n\nRun ID: ${runId}\nStatus: ${run.status || 'audited'}\n`
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = Object.assign(document.createElement('a'), { href: url, download: `omnisight-report-${runId}.md` })
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    return
  }
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/export/markdown`, { headers: authHeaders(getToken()) })
  await checkResponse(res)
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: `omnisight-report-${runId}.md` })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function downloadReportJson(runId) {
  if (DATA_SOURCE === 'mock') {
    const run = fixtureRuns.find((r) => r.run_id === runId) || {}
    const blob = new Blob([JSON.stringify(run, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = Object.assign(document.createElement('a'), { href: url, download: `omnisight-run-${runId}.json` })
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    return
  }
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/export/json`, { headers: authHeaders(getToken()) })
  await checkResponse(res)
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: `omnisight-run-${runId}.json` })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function downloadReportSarif(runId) {
  if (DATA_SOURCE === 'mock') {
    const blob = new Blob([JSON.stringify({ version: '2.1.0', runs: [] }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = Object.assign(document.createElement('a'), { href: url, download: `omnisight-${runId}.sarif` })
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    return
  }
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/export/sarif`, { headers: authHeaders(getToken()) })
  await checkResponse(res)
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: `omnisight-${runId}.sarif` })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function compareRuns(baseId, candId) {
  if (DATA_SOURCE === 'mock') {
    return { baseline_run_id: baseId, candidate_run_id: candId, net_improvement_percentage: 100.0, is_improved: true }
  }
  const res = await fetch(`/api/runs/${encodeURIComponent(baseId)}/compare/${encodeURIComponent(candId)}`, {
    headers: authHeaders(getToken()),
  })
  await checkResponse(res)
  return res.json()
}

export async function addRunTag(runId, tag) {
  if (DATA_SOURCE === 'mock') return { run_id: runId, tags: [tag] }
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/tags`, {
    method: 'POST',
    headers: { ...authHeaders(getToken()), 'Content-Type': 'application/json' },
    body: JSON.stringify({ tag }),
  })
  await checkResponse(res)
  return res.json()
}

export async function removeRunTag(runId, tag) {
  if (DATA_SOURCE === 'mock') return { run_id: runId, tags: [] }
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/tags/${encodeURIComponent(tag)}`, {
    method: 'DELETE',
    headers: authHeaders(getToken()),
  })
  await checkResponse(res)
  return res.json()
}

// Real-time Server-Sent Events (SSE) subscription for sub-second run state updates.
export function subscribeRunEvents(runId, onEvent) {
  if (DATA_SOURCE === 'mock' || typeof EventSource === 'undefined') return () => {}
  try {
    const es = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events`)
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data && onEvent) onEvent(data)
      } catch {}
    }
    es.onerror = () => {
      es.close()
    }
    return () => es.close()
  } catch {
    return () => {}
  }
}
