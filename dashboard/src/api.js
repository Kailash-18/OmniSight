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
