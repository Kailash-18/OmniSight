// Session token for the live backend. sessionStorage: cleared when the tab closes.
const TOKEN = 'omnisight.token'
const USER = 'omnisight.user'
let unauthorizedHandler = null
let memory = {} // fallback when storage is blocked (private mode etc.)

const store = () => { try { return globalThis.sessionStorage } catch { return null } }
const read = (k) => { try { return store()?.getItem(k) ?? null } catch { return null } }
const write = (k, v) => {
  memory[k] = v
  try { v == null ? store()?.removeItem(k) : store()?.setItem(k, v) } catch { /* memory only */ }
}

export const getToken = () => read(TOKEN) ?? memory[TOKEN] ?? null
export const getUser = () => read(USER) ?? memory[USER] ?? null
export function setSession({ token, username }) { write(TOKEN, token); write(USER, username) }
export function clearSession() { write(TOKEN, null); write(USER, null); memory = {} }
export const authHeaders = (token) => (token ? { Authorization: `Bearer ${token}` } : {})
export function onUnauthorized(fn) { unauthorizedHandler = fn }

// Throws an Error with .status for non-2xx; a 401 ends the session and notifies the app once.
export async function checkResponse(res) {
  if (res.ok) return res
  let message = `Backend returned HTTP ${res.status}`
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') message = body.detail
  } catch { /* not json */ }
  if (res.status === 401) {
    const hadSession = getToken() != null
    clearSession()
    if (hadSession) unauthorizedHandler?.()
  }
  throw Object.assign(new Error(message), { status: res.status })
}
