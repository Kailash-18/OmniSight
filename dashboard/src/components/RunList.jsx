import { useEffect, useState } from 'react'
import { Search, RefreshCw, ExternalLink, ListChecks } from 'lucide-react'
import { listRuns, DATA_SOURCE } from '../api.js'
import { STATUSES, formatTime } from '../format.js'
import { relativeTime } from '../lifecycle.js'
import StatusBadge from './StatusBadge.jsx'
import MockTag from './MockTag.jsx'
import TargetLink from './TargetLink.jsx'

export default function RunList({ link }) {
  const [state, setState] = useState({ loading: true, error: null, runs: [] })
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')

  const load = () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    listRuns()
      .then((runs) => setState({ loading: false, error: null, runs }))
      .catch((error) => setState({ loading: false, error, runs: [] }))
  }
  useEffect(load, [])

  const q = query.trim().toLowerCase()
  const shown = state.runs
    .filter((r) => filter === 'all' || r.status === filter)
    .filter((r) => !q || r.run_id.toLowerCase().includes(q) || String(r.target || '').toLowerCase().includes(q))

  return (
    <section className="run-hero">
      <header className="page-head">
        <div>
          <h1>Runs</h1>
          <p className="muted">{state.loading ? 'Loading…' : `${state.runs.length} ${state.runs.length === 1 ? 'run' : 'runs'}`}</p>
        </div>
      </header>

      <div className="toolbar" role="search">
        <span className="input-wrap">
          <Search size={16} className="input-icon" aria-hidden="true" />
          <input className="input with-icon" placeholder="Search by run or address" value={query} onChange={(e) => setQuery(e.target.value)}
            aria-label="Search runs" data-testid="runs-search" />
        </span>
        <select className="input" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter by status" data-testid="status-filter">
          <option value="all">All statuses</option>
          {Object.entries(STATUSES).map(([value, { label }]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <button type="button" className="btn" data-testid="runs-refresh" onClick={load}><RefreshCw size={15} aria-hidden="true" />Refresh</button>
      </div>

      {state.loading ? (
        <div className="panel table-panel" data-testid="runs-loading" aria-busy="true">
          {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton skeleton-row" />)}
        </div>
      ) : state.error ? (
        <div className="panel empty" data-testid="runs-error" role="alert">
          <h2>Couldn’t load runs</h2>
          <p>{state.error.message}</p>
          {DATA_SOURCE === 'live' && <p className="small">Check that the backend is running on port 8000.</p>}
          <button type="button" className="btn" data-testid="runs-retry" onClick={load}>Try again</button>
        </div>
      ) : shown.length === 0 ? (
        <div className="panel empty" data-testid="runs-empty">
          <ListChecks size={28} aria-hidden="true" />
          <h2>{state.runs.length === 0 ? 'No runs yet' : 'No runs match'}</h2>
          {state.runs.length === 0
            ? <p>Start one from the <a {...link('/')}>overview</a>.</p>
            : <p>Try another status or search.</p>}
        </div>
      ) : (
        <div className="panel table-panel">
          <table className="runs" data-testid="runs-table">
            <thead>
              <tr><th>Run</th><th>Status</th><th>Started</th><th>Address</th><th className="num">Bugs</th><th>PR</th></tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.run_id} data-testid={`run-row-${r.run_id}`}>
                  <td data-label="Run"><a className="run-link mono" {...link(`/runs/${encodeURIComponent(r.run_id)}`)}>{r.run_id}</a><MockTag /></td>
                  <td data-label="Status"><StatusBadge status={r.status} /></td>
                  <td data-label="Started" title={formatTime(r.start_time)}>{relativeTime(r.start_time)}</td>
                  <td data-label="Address" className="mono"><TargetLink target={r.target} /></td>
                  <td data-label="Bugs" className="num">{r.issue_count}</td>
                  <td data-label="PR">
                    {r.pr_url
                      ? <a href={r.pr_url} target="_blank" rel="noreferrer" aria-label={`Open pull request for ${r.run_id}`}><ExternalLink size={15} aria-hidden="true" /></a>
                      : <span className="muted">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
