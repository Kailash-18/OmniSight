// Data source switch: fixtures (default) or the live backend via the Vite /api proxy.
// Run with VITE_DATA_SOURCE=live npm run dev to read from FastAPI on :8000.
import fixtureRuns from './fixtures/runs.json'
import { toSummary } from './format.js'

export const DATA_SOURCE = import.meta.env.VITE_DATA_SOURCE === 'live' ? 'live' : 'mock'

async function getJson(path) {
  const res = await fetch('/api' + path)
  if (!res.ok) {
    const err = new Error(res.status === 404 ? 'Run not found' : `Backend returned HTTP ${res.status}`)
    err.status = res.status
    throw err
  }
  return res.json()
}

async function postJson(path, payload = {}) {
  const res = await fetch('/api' + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    let msg = `Backend returned HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) msg = body.detail
    } catch {
      // ignore
    }
    const err = new Error(msg)
    err.status = res.status
    throw err
  }
  return res.json()
}

export async function listRuns() {
  const runs = DATA_SOURCE === 'mock' ? fixtureRuns : await getJson('/runs')
  return runs.map(toSummary)
}

export async function getRun(runId) {
  if (DATA_SOURCE === 'live') return getJson(`/runs/${encodeURIComponent(runId)}`)
  const run = fixtureRuns.find((r) => r.run_id === runId)
  if (!run) throw Object.assign(new Error('Run not found'), { status: 404 })
  return run
}

export async function createPullRequest(runId, payload = {}) {
  if (DATA_SOURCE === 'mock') {
    const prNumber = Math.abs(runId.split('').reduce((a, b) => (a << 5) - a + b.charCodeAt(0), 0)) % 1000 + 10
    const prUrl = `https://github.com/Kailash-18/OmniSight/pull/${prNumber}`
    const run = fixtureRuns.find((r) => r.run_id === runId)
    if (run) {
      run.pr_url = prUrl
      run.status = 'pr_opened'
    }
    return { status: 'success', run_id: runId, pr_url: prUrl, message: 'Pull Request created successfully.' }
  }
  return postJson(`/runs/${encodeURIComponent(runId)}/create-pr`, payload)
}

export async function fetchMilestones() {
  if (DATA_SOURCE === 'mock') {
    return {
      member: 'Member 1 - Backend & PR Automation',
      week_3_pr_automation: 'in_progress',
      week_3_progress: '50% - Human-in-the-Loop review controls and PR automation',
    }
  }
  return getJson('/milestones')
}
