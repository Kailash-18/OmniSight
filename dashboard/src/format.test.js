import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import {
  STATUSES, statusMeta, formatConfidence, formatTime, parseShot, pairEvidence,
  evidenceUrl, toSummary, diffLines, validatorErrors, safeUrl, defectPage,
} from './format.js'

const runs = JSON.parse(readFileSync(new URL('./fixtures/runs.json', import.meta.url)))

test('status enum matches the contract exactly', () => {
  assert.deepEqual(Object.keys(STATUSES).sort(), [
    'audited', 'failed', 'fixed', 'needs_review', 'patch_rejected', 'pr_opened', 'queued', 'running', 'verifying',
  ])
  assert.equal(statusMeta('fixed').tone, 'good')
  assert.equal(statusMeta('brand_new').label, 'brand_new') // unknown status still visible
  assert.equal(statusMeta(undefined).label, 'Unknown')
})

test('confidence and time formatting', () => {
  assert.equal(formatConfidence(0.96), '96%')
  assert.equal(formatConfidence(1.4), '—')
  assert.equal(formatConfidence(undefined), '—')
  assert.equal(formatTime('nope'), '—')
  assert.match(formatTime('2026-10-22T10:00:00Z'), /UTC$/)
})

test('screenshot names parse for both runner and contract styles', () => {
  assert.deepEqual(parseShot('artifacts/runs/r1/screenshots/mobile_390x844_cart.png'),
    { key: 'mobile_390x844_cart', viewport: 'mobile_390x844', page: 'cart' })
  assert.equal(parseShot('artifacts/runs/r1/retest/mobile_390x844_cart_after.png').key, 'mobile_390x844_cart')
  assert.equal(parseShot('retest_desktop_1280x800_checkout.png').key, 'desktop_1280x800_checkout')
  assert.equal(parseShot('weird.png').viewport, null)
})

test('before/after pairing matches by viewport and page', () => {
  const pairs = pairEvidence({
    before_screenshots: ['a/desktop_1440x900_home.png', 'a/mobile_375x667_cart.png'],
    after_screenshots: ['a/retest/desktop_1440x900_home_after.png', 'a/retest/desktop_1280x800_checkout_after.png'],
  })
  assert.equal(pairs.length, 3)
  const home = pairs.find((p) => p.key === 'desktop_1440x900_home')
  assert.equal(home.after, 'a/retest/desktop_1440x900_home_after.png')
  assert.equal(pairs.find((p) => p.key === 'mobile_375x667_cart').after, null) // no retest
  assert.equal(pairs.find((p) => p.key === 'desktop_1280x800_checkout').before, null) // orphan after
  assert.deepEqual(pairEvidence(undefined), [])
})

test('fixtures: every screenshot exists and each after matches its before viewport', () => {
  for (const run of runs) {
    assert.match(run.run_id, /^mock-/)
    for (const pair of pairEvidence(run.evidence_paths)) {
      for (const p of [pair.before, pair.after].filter(Boolean)) {
        assert.ok(existsSync(new URL('../public/' + p, import.meta.url)), `missing ${p}`)
      }
      if (pair.after) assert.ok(pair.before, `${run.run_id}: after without before (${pair.key})`)
    }
  }
})

test('store links: only http(s), defect page derived from evidence', () => {
  assert.equal(safeUrl('http://localhost:5173'), 'http://localhost:5173/')
  assert.equal(safeUrl('javascript:alert(1)'), null)
  assert.equal(safeUrl('not a url'), null)

  const byId = (id) => runs.find((r) => r.run_id === id)
  const home = defectPage(byId('mock-run-1003').target, byId('mock-run-1003').findings[0], byId('mock-run-1003').evidence_paths)
  assert.deepEqual(home, { url: 'http://localhost:5173/', page: 'Products', viewport: 'desktop_1440x900', size: '1440×900', steps: [] })
  const cart = defectPage(byId('mock-run-1002').target, byId('mock-run-1002').findings[0], byId('mock-run-1002').evidence_paths)
  assert.equal(cart.page, 'Cart')
  assert.deepEqual(cart.steps, ['Add any product', 'Open Cart'])
  const checkout = defectPage(byId('mock-run-1001').target, byId('mock-run-1001').findings[0], byId('mock-run-1001').evidence_paths)
  assert.equal(checkout.page, 'Checkout')
  assert.equal(checkout.steps.length, 3)
  // finding viewport "all" falls back to the first screenshot
  assert.equal(defectPage('http://localhost:5173', { viewport: 'all' }, byId('mock-run-1001').evidence_paths).page, 'Checkout')
  assert.equal(defectPage('javascript:x', {}, byId('mock-run-1001').evidence_paths), null) // unsafe target
  assert.equal(defectPage('http://localhost:5173', {}, undefined), null) // no evidence
})

test('summary, diff and validator helpers', () => {
  const s = toSummary(runs.find((r) => r.run_id === 'mock-run-1001'))
  assert.deepEqual(Object.keys(s), ['run_id', 'start_time', 'target', 'status', 'issue_count', 'pr_url'])
  assert.equal(s.issue_count, 1)
  assert.equal(toSummary({ run_id: 'x', issue_count: 4 }).issue_count, 4)
  assert.deepEqual(diffLines('-a\n+b\n c').map((l) => l.kind), ['del', 'add', 'ctx'])
  assert.deepEqual(validatorErrors({ validator_errors: 'bad' }), ['bad'])
  assert.deepEqual(validatorErrors({ validator_errors: null }), [])
  assert.equal(evidenceUrl('fixtures/a.png'), '/fixtures/a.png')
  assert.equal(evidenceUrl('artifacts/runs/r1/x.png'), '/artifacts/runs/r1/x.png')
  // runner output is absolute (browser_runner.py appends str(Path))
  assert.equal(evidenceUrl('/Users/me/OmniSight/artifacts/runs/r1/screenshots/x.png'), '/artifacts/runs/r1/screenshots/x.png')
  assert.equal(evidenceUrl('C:\\work\\OmniSight\\artifacts\\runs\\r1\\x.png'), '/artifacts/runs/r1/x.png')
  assert.equal(evidenceUrl(null), null)
})
