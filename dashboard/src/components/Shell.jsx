import { LayoutDashboard, ListChecks, Moon, Sun, LogOut, Radio } from 'lucide-react'
import { DATA_SOURCE } from '../api.js'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, match: (p) => p === '/' || p === '/login' },
  { to: '/runs', label: 'Runs', icon: ListChecks, match: (p) => p.startsWith('/runs') },
]

export default function Shell({ user, theme, onTheme, onLogout, link, path, children }) {
  return (
    <div className="app-shell">
      <nav className="sidebar" aria-label="Main">
        <a className="brand" data-testid="brand-link" {...link('/')}><span className="logo-mark" aria-hidden="true" />OmniSight</a>
        {NAV.map(({ to, label, icon: Icon, match }) => (
          <a key={to} className={`nav-item${match(path) ? ' active' : ''}`} aria-current={match(path) ? 'page' : undefined} {...link(to)}>
            <Icon size={18} aria-hidden="true" />{label}
          </a>
        ))}
        <div className="sidebar-foot">
          <span className={`pill ${DATA_SOURCE === 'mock' ? 'tone-warn' : 'tone-good'}`} data-testid="data-source">
            <Radio size={14} aria-hidden="true" />{DATA_SOURCE === 'mock' ? 'Mock data' : 'Live'}
          </span>
          <button type="button" className="btn btn-ghost btn-small" onClick={onTheme} data-testid="theme-toggle"
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
            {theme === 'dark' ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
          {user && (
            <div className="user-row">
              <span className="avatar" aria-hidden="true">{user[0]?.toUpperCase()}</span>
              <span className="user-name" data-testid="signed-in-user">{user}</span>
              <button type="button" className="icon-btn" onClick={onLogout} aria-label="Log out" title="Log out" data-testid="logout">
                <LogOut size={16} aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
      </nav>
      <div className="content">
        {DATA_SOURCE === 'mock' && (
          <div className="mock-banner" role="note" data-testid="mock-banner">
            <strong>Mock Data</strong>: these runs are samples from <code>dashboard/src/fixtures/runs.json</code>, not real OmniSight results.
          </div>
        )}
        <main className="page">{children}</main>
      </div>
    </div>
  )
}
