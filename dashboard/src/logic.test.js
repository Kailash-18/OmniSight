import { test } from 'node:test'
import assert from 'node:assert/strict'
import { authHeaders, checkResponse, onUnauthorized, setSession, getToken } from './auth.js'
import { readTheme, writeTheme } from './theme.js'
import { lifecycle, stats, clampPercent, isActiveStatus, relativeTime, shouldPoll, ciMeta } from './lifecycle.js'

// sessionStorage shim for node
globalThis.sessionStorage = { s: {}, getItem(k) { return this.s[k] ?? null }, setItem(k, v) { this.s[k] = String(v) }, removeItem(k) { delete this.s[k] } }

test('authHeaders adds bearer only with a token', () => {
  assert.deepEqual(authHeaders('abc'), { Authorization: 'Bearer abc' })
  assert.deepEqual(authHeaders(null), {})
})

test('checkResponse 401 calls onUnauthorized once and throws', async () => {
  setSession({ token: 't', username: 'u' })
  let calls = 0
  onUnauthorized(() => { calls++ })
  const res401 = { ok: false, status: 401, json: async () => ({ detail: 'Not authenticated' }) }
  await assert.rejects(checkResponse(res401), (e) => e.status === 401)
  await assert.rejects(checkResponse(res401), (e) => e.status === 401)
  assert.equal(calls, 1) // second 401 after the session is gone doesn't re-fire
  assert.equal(getToken(), null)
})

test('checkResponse surfaces backend detail and passes ok responses', async () => {
  await assert.rejects(checkResponse({ ok: false, status: 409, json: async () => ({ detail: 'A run is already in progress: r1' }) }),
    (e) => e.status === 409 && /already in progress/.test(e.message))
  const ok = { ok: true, status: 200 }
  assert.equal(await checkResponse(ok), ok)
})

test('readTheme falls back to dark when storage throws or is empty', () => {
  const broken = { getItem() { throw new Error('blocked') }, setItem() { throw new Error('blocked') } }
  assert.equal(readTheme(broken), 'dark')
  assert.equal(writeTheme('light', broken), false)
  const mem = { v: null, getItem() { return this.v }, setItem(_, v) { this.v = v } }
  assert.equal(readTheme(mem), 'dark')
  writeTheme('light', mem)
  assert.equal(readTheme(mem), 'light')
  mem.v = 'neon'
  assert.equal(readTheme(mem), 'dark')
})

test('lifecycle marks progress, failure and fixed-without-patch', () => {
  const states = (s, extra = {}) => lifecycle({ status: s, ...extra }).map((x) => `${x.key}:${x.state}`)
  assert.deepEqual(states('running'), ['queued:done', 'running:current', 'audited:todo', 'verifying:todo', 'fixed:todo', 'pr_opened:todo'])
  assert.deepEqual(states('fixed'), ['queued:done', 'running:done', 'audited:done', 'verifying:done', 'fixed:done', 'pr_opened:todo'])
  assert.deepEqual(states('fixed', { patch: null, findings: [] }).slice(3, 5), ['verifying:skipped', 'fixed:done'])
  assert.ok(states('failed').includes('running:failed'))
  assert.ok(states('patch_rejected').includes('verifying:failed'))
  assert.equal(lifecycle({ status: 'pr_opened' }).at(-1).state, 'done')
})

test('stats of empty list and mixed runs', () => {
  assert.deepEqual(stats([]), { total: 0, bugs: 0, fixRate: '—', prs: 0 })
  const s = stats([
    { status: 'fixed', issue_count: 3, pr_url: null },
    { status: 'pr_opened', issue_count: 2, pr_url: 'x' },
    { status: 'needs_review', issue_count: 1 },
    { status: 'running', issue_count: 0 },
  ])
  assert.deepEqual(s, { total: 4, bugs: 6, fixRate: '67%', prs: 1 })
})

test('clampPercent, isActiveStatus, relativeTime', () => {
  assert.equal(clampPercent(-5), 0); assert.equal(clampPercent(140), 100); assert.equal(clampPercent(NaN), 50)
  assert.equal(isActiveStatus('running'), true); assert.equal(isActiveStatus('fixed'), false)
  const now = Date.parse('2026-11-05T10:00:00Z')
  assert.equal(relativeTime('2026-11-05T09:59:30Z', now), 'just now')
  assert.equal(relativeTime('2026-11-05T09:55:00Z', now), '5 min ago')
  assert.equal(relativeTime('2026-11-05T07:00:00Z', now), '3 h ago')
  assert.equal(relativeTime('bad', now), '—')
})

test('shouldPoll keeps a launched run live through "audited" until the backend says it ended', () => {
  assert.equal(shouldPoll({ run_id: 'r1', status: 'running' }, null), true)
  assert.equal(shouldPoll({ run_id: 'r1', status: 'audited' }, 'r1'), true)   // mid-run audited
  assert.equal(shouldPoll({ run_id: 'r1', status: 'audited' }, null), false)  // finished as audited
  assert.equal(shouldPoll({ run_id: 'r1', status: 'fixed' }, 'r2'), false)
  assert.equal(shouldPoll(null, 'r1'), false)
})

test('ciMeta labels every CI state and says when to keep checking', () => {
  assert.deepEqual(ciMeta({ state: 'passed', total: 4, passed: 4 }), { label: 'CI passed', tone: 'good', detail: '4 of 4 checks passed', poll: false })
  assert.equal(ciMeta({ state: 'failed', total: 4, failed: 1 }).detail, '1 of 4 checks failed')
  assert.equal(ciMeta({ state: 'running', total: 3, running: 2 }).poll, true)
  assert.equal(ciMeta({ state: 'pending' }).poll, true)
  assert.equal(ciMeta({ state: 'unavailable' }).tone, 'neutral')
  assert.equal(ciMeta(undefined).label, 'CI status unknown')
})
