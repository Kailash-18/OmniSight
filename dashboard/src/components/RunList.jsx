import { useEffect, useState } from 'react'
import { listRuns, DATA_SOURCE } from '../api.js'
import { STATUSES, formatTime } from '../format.js'
import StatusBadge from './StatusBadge.jsx'
import MockTag from './MockTag.jsx'
import TargetLink from './TargetLink.jsx'

export default function RunList({ link }) {
  const [state, setState] = useState({ loading: true, error: null, runs: [] })
  const [filter, setFilter] = useState('all')

  const load = () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    listRuns()
      .then((runs) => setState({ loading: false, error: null, runs }))
      .catch((error) => setState({ loading: false, error, runs: [] }))
  }
  useEffect(load, [])

  if (state.loading) return <section className="panel state" data-testid="runs-loading" aria-busy="true">Loading runs…</section>

  if (state.error)
    return (
      <section className="panel state state-error" data-testid="runs-error" role="alert">
        <h1>Couldn't load runs</h1>
        <p>{state.error.message}</p>
        {DATA_SOURCE === 'live' && <p className="muted">Is the backend running? <code>uvicorn app.main:app --port 8000</code> in <code>backend/</code></p>}
        <button type="button" className="btn" data-testid="runs-retry" onClick={load}>Retry</button>
      </section>
    )

  const shown = filter === 'all' ? state.runs : state.runs.filter((r) => r.status === filter)

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Runs</h1>
          <p className="muted">{state.runs.length} run{state.runs.length === 1 ? '' : 's'}</p>
        </div>
        <label className="filter">
          <span>Status</span>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} data-testid="status-filter">
            <option value="all">All statuses</option>
            {Object.entries(STATUSES).map(([value, { label }]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </div>

      {shown.length === 0 ? (
        <div className="panel state" data-testid="runs-empty">
          <h2>{state.runs.length === 0 ? 'No runs yet' : 'No runs with this status'}</h2>
          <p className="muted">
            {state.runs.length === 0 ? 'Trigger a run with POST /webhook/build or the automation CLI.' : 'Pick another status filter.'}
          </p>
        </div>
      ) : (
        <table className="runs panel" data-testid="runs-table">
          <thead>
            <tr><th>Run</th><th>Status</th><th>Started</th><th>Target</th><th className="num">Issues</th><th>PR</th></tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.run_id} data-testid={`run-row-${r.run_id}`}>
                <td data-label="Run"><a className="run-link" {...link(`/runs/${encodeURIComponent(r.run_id)}`)}>{r.run_id}</a> <MockTag /></td>
                <td data-label="Status"><StatusBadge status={r.status} /></td>
                <td data-label="Started">{formatTime(r.start_time)}</td>
                <td data-label="Target" className="mono"><TargetLink target={r.target} /></td>
                <td data-label="Issues" className="num">{r.issue_count}</td>
                <td data-label="PR">{r.pr_url ? <a href={r.pr_url} target="_blank" rel="noreferrer">Open PR</a> : <span className="muted">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
