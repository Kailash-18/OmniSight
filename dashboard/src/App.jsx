import { useEffect, useState } from 'react'
import { DATA_SOURCE, me } from './api.js'
import { clearSession, getToken, getUser, onUnauthorized } from './auth.js'
import { applyTheme, readTheme, writeTheme } from './theme.js'
import Shell from './components/Shell.jsx'
import Login from './components/Login.jsx'
import Overview from './components/Overview.jsx'
import RunList from './components/RunList.jsx'
import RunDetail from './components/RunDetail.jsx'
import { ShortcutsModal } from './components/ShortcutsModal.jsx'
import { ToastProvider } from './components/Toast.jsx'

// ponytail: four routes, so a pushState switch replaces a router library (same as app-under-test).
const matchRun = (path) => path.match(/^\/runs\/([^/]+)\/?$/)
const needsLogin = DATA_SOURCE === 'live'

export default function App() {
  const [path, setPath] = useState(window.location.pathname)
  const [user, setUser] = useState(needsLogin ? getUser() : 'demo')
  const [expired, setExpired] = useState(false)
  const [theme, setTheme] = useState(readTheme())
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  const go = (to) => {
    window.history.pushState(null, '', to)
    setPath(to)
    window.scrollTo(0, 0)
  }
  const link = (to) => ({
    href: to,
    onClick: (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
      e.preventDefault()
      go(to)
    },
  })

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    onUnauthorized(() => { setUser(null); setExpired(true) })
    if (needsLogin && getToken()) me().then((r) => setUser(r.username)).catch(() => {})

    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        e.preventDefault()
        setShortcutsOpen((o) => !o)
      } else if (e.key === 'Escape') {
        setShortcutsOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('popstate', onPop)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  const toggleTheme = () => {
    const t = theme === 'dark' ? 'light' : 'dark'
    setTheme(t)
    applyTheme(t)
    writeTheme(t)
  }
  const logout = () => { clearSession(); setUser(null); setExpired(false); go('/login') }

  if (needsLogin && !user) {
    return (
      <Login expired={expired} onSignedIn={(name) => {
        setUser(name)
        setExpired(false)
        if (path === '/login') go('/')
      }} />
    )
  }

  const runMatch = matchRun(path)
  let page
  if (path === '/' || path === '/login') page = <Overview link={link} />
  else if (path === '/runs') page = <RunList link={link} />
  else if (runMatch) page = <RunDetail runId={decodeURIComponent(runMatch[1])} link={link} />
  else page = (
    <section className="panel empty" data-testid="page-not-found">
      <h1>Page not found</h1>
      <p>This address doesn’t match any page.</p>
      <a className="btn" {...link('/')}>Go to overview</a>
    </section>
  )

  return (
    <ToastProvider>
      <Shell user={needsLogin ? user : null} theme={theme} onTheme={toggleTheme} onLogout={logout} link={link} path={path}>
        {page}
      </Shell>
      <ShortcutsModal isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </ToastProvider>
  )
}
