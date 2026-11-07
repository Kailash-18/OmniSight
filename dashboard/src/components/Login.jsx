import { useState } from 'react'
import { Eye, EyeOff, LoaderCircle, ScanLine, ShieldCheck, GitPullRequest } from 'lucide-react'
import { login } from '../api.js'

export default function Login({ onSignedIn, expired }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(expired ? 'Your session expired. Sign in again to continue.' : null)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const s = await login(username.trim(), password)
      onSignedIn(s.username)
    } catch (err) {
      setError(err.status === 401 ? 'That username and password don’t match.' : err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login" data-testid="login-page">
      <aside className="login-art">
        <div className="login-brand"><span className="logo-mark" aria-hidden="true" />OmniSight</div>
        <h1>Find the bug before your users do.</h1>
        <div className="scope" aria-hidden="true">
          <div className="scope-bar"><i /><i /><i /></div>
          <div className="scope-body"><i /><i /><i /></div>
          <div className="scope-cta" />
          <div className="scope-reticle" />
        </div>
        <ul className="login-points">
          <li><ScanLine size={18} aria-hidden="true" />Walks your site on desktop and mobile</li>
          <li><ShieldCheck size={18} aria-hidden="true" />Proposes a fix and checks it works</li>
          <li><GitPullRequest size={18} aria-hidden="true" />Hands you a pull request to review</li>
        </ul>
      </aside>
      <main className="login-main">
        <form className="login-card panel" onSubmit={submit} noValidate>
          <h2>Sign in</h2>
          <p className="muted">Sign in with administrator credentials (<code>admin / admin</code>).</p>
          <label className="field">Username
            <input className="input" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)}
              required data-testid="login-username" autoFocus />
          </label>
          <label className="field">Password
            <span className="input-wrap">
              <input className="input" type={show ? 'text' : 'password'} autoComplete="current-password" value={password}
                onChange={(e) => setPassword(e.target.value)} required data-testid="login-password" />
              <button type="button" className="icon-btn" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
                {show ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </span>
          </label>
          {error && <p className="alert" role="alert" data-testid="login-error">{error}</p>}
          <button className="btn btn-primary btn-block" disabled={busy || !username.trim() || !password} data-testid="login-submit">
            {busy ? <><LoaderCircle className="spin" size={18} aria-hidden="true" />Signing in…</> : 'Sign in'}
          </button>
        </form>
      </main>
    </div>
  )
}
