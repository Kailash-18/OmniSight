# OmniSight QA Dashboard

React page where a reviewer looks at OmniSight runs: status, findings, before/after screenshots,
the proposed patch, and an approve/reject decision.

Owner: Member 2. React 18 + Vite 6, plain CSS. No backend code of its own.

## Run

```bash
cd dashboard
npm install
npm run dev                          # http://localhost:5180  (mock data, default)
VITE_DATA_SOURCE=live npm run dev    # reads the FastAPI backend instead
```

| Command | What it does |
| --- | --- |
| `npm run dev` | Dev server at **http://localhost:5180** (port is fixed) |
| `npm run build` | Production build into `dist/` |
| `npm test` | Helper + fixture tests (`node:test`, no extra deps) |

**Why port 5180:** `automation/health_check.py` probes 5174 and 5175 as fallback store ports and accepts any
page containing `root`, so the dashboard stays off those ports to avoid being mistaken for the store.

## Data sources

| Mode | Where data comes from | How it's labelled |
| --- | --- | --- |
| `mock` (default) | `src/fixtures/runs.json` | Purple **Mock Data** banner, a "Mock data" pill in the header, a **MOCK** tag on every run id, and every id starts with `mock-` |
| `live` | `GET /runs` and `GET /runs/{run_id}` on the backend (`127.0.0.1:8000`) | "Live API" pill, no mock labels |

- **Proxy:** in live mode the dev server forwards `/api/*` to the backend (`/api/runs` → `:8000/runs`).
  Calls stay same-origin, so the dashboard never hardcodes the backend URL (the backend also allows CORS now).
- **Evidence files:** live runs reference files like `artifacts/runs/<id>/screenshots/x.png`. The dev server serves
  the repo's `artifacts/` folder at `/artifacts/...` (PNG and JSON only, no path traversal). This is dev-only; long term
  the backend should serve evidence.

Fields follow `docs/api-contract.md`. The live backend sends the baseline screenshots as `evidence_paths.screenshots`
(absolute paths) instead of the contract's `before_screenshots`; both are accepted. When the evidence covers several
pages at a finding's viewport, the defect link says "Open store" rather than guessing the page. Fields that only some producers send (`target_element`, `error`,
`retest_verification.mismatch_percentage`, `patch.validation_status`/`validator_errors`) are optional and only shown
when present. Unknown status values still render as a neutral badge. Only `http(s)` targets become links; anything
else (e.g. `javascript:`) is shown as plain text.

Fixture targets use `http://localhost:5173`, not `127.0.0.1`: on macOS Vite binds the store to `[::1]` (IPv6 localhost),
so `127.0.0.1:5173` doesn't load in a browser there.

## Mock fixtures

`src/fixtures/runs.json` has 6 runs, one per state the UI must handle:

| Run | Status | Shows |
| --- | --- | --- |
| `mock-run-1001` | `fixed` | Defect 3 (Submit obstructed), desktop 1280×800, before/after, valid patch |
| `mock-run-1002` | `needs_review` | Defect 2 (button clipped), mobile 390×844, before/after, 71% confidence |
| `mock-run-1003` | `fixed` | Defect 1 (heading overlap), desktop 1440×900, before/after |
| `mock-run-1004` | `patch_rejected` | Same defect, before only, patch rejected by the allowlist validator |
| `mock-run-1005` | `failed` | Run error message, no evidence |
| `mock-run-1006` | `running` | In-progress run, nothing captured yet |

### Fixture screenshots (`public/fixtures/`)

| File | Source |
| --- | --- |
| `desktop_1440x900_home.png`, `mobile_390x844_cart.png`, `desktop_1280x800_checkout.png` | **Before:** real output of `automation/browser_runner.py` against the buggy store |
| `*_after.png` (same three) | **After:** captured with the runner's own browser settings and journey, with `defects.css` removed live in the page (the repaired layout). Made for mock data; the store source wasn't changed. |

"After" files use the runner's real naming (`{viewport}_{page}_after.png`). The pairing logic also accepts the
contract example's `retest_` prefix. These PNGs are committed through one narrow root `.gitignore` exception:
`!dashboard/public/fixtures/*.png`.

## Pages

- **`/`, run list:** run id, status, start time (UTC), target (clickable link to the store), issue count, PR link. Filter by status. Turns into cards on phones.
- **`/runs/:run_id`, run detail:**
  - Summary (retries, PR, steps, error).
  - Findings (category, severity, viewport, element, confidence bar, suggested fix, rationale).
  - **Defect page link** per finding: "Open Cart page ↗" opens the store in a new tab, with the steps to see the
    defect live (viewport size, plus "Add any product → Open Cart" for cart/checkout). It links to the store home,
    not `/cart` or `/checkout`, because the store's cart is in memory and a direct link would open an empty page.
    The page comes from the finding's screenshot name.
  - Before/after screenshots paired by viewport and page.
  - Patch diff with its validation result.
  - Review panel.
- **States:** loading, empty, filter-empty, backend error with retry, run not found, unknown page, missing screenshot,
  and image failed to load.

## Review state

Approve/Reject (with an optional note) is **saved in the browser only** (`localStorage`). The backend has no review
endpoint yet, and this never approves or merges anything on GitHub. Patches the validator rejected can't be approved.

## Test IDs

`mock-banner`, `data-source`, `mock-tag`, `status-filter`, `runs-table`, `run-row-{run_id}`, `status-badge`
(`data-status`), `runs-loading`, `runs-error`, `runs-retry`, `runs-empty`, `run-detail`, `back-to-runs`,
`retry-count`, `pr-link`, `run-error-message`, `finding-{id}`, `confidence`, `evidence-pair-{viewport}_{page}`,
`shot-missing`, `shot-failed`, `patch-valid`, `patch-invalid`, `validator-errors`, `patch-diff`, `review-panel`,
`review-note`, `review-approve`, `review-reject`, `review-result`, `review-unavailable`, `run-not-found`, `page-not-found`.
