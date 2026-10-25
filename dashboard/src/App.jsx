import { useEffect, useState } from 'react'
import { DATA_SOURCE } from './api.js'
import RunList from './components/RunList.jsx'
import RunDetail from './components/RunDetail.jsx'

// ponytail: two routes, so a pushState switch replaces a router library (same as app-under-test).
const matchRun = (path) => path.match(/^\/runs\/([^/]+)\/?$/)

export default function App() {
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const link = (to) => ({
    href: to,
    onClick: (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
      e.preventDefault()
      window.history.pushState(null, '', to)
      setPath(to)
      window.scrollTo(0, 0)
    },
  })

  const runMatch = matchRun(path)
  let page
  if (path === '/') page = <RunList link={link} />
  else if (runMatch) page = <RunDetail runId={decodeURIComponent(runMatch[1])} link={link} />
  else
    page = (
      <section className="panel state" data-testid="page-not-found">
        <h1>Page not found</h1>
        <a className="btn" {...link('/')}>Back to runs</a>
      </section>
    )

  return (
    <>
      <header className="topbar">
        <div className="wrap topbar-inner">
          <a className="brand" data-testid="brand-link" {...link('/')}>OmniSight <span>QA</span></a>
          <span className={`source source-${DATA_SOURCE}`} data-testid="data-source">
            {DATA_SOURCE === 'mock' ? 'Mock data' : 'Live API'}
          </span>
        </div>
      </header>
      {DATA_SOURCE === 'mock' && (
        <div className="mock-banner" role="note" data-testid="mock-banner">
          <div className="wrap">
            <strong>Mock Data</strong> — these runs are fixtures from <code>dashboard/src/fixtures/runs.json</code>, not live
            OmniSight results.
          </div>
        </div>
      )}
      <main className="wrap main">{page}</main>
    </>
  )
}
