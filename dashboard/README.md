# OmniSight Dashboard

The console where a reviewer starts an OmniSight test, watches it run, and reviews what it found: the defects, before/after screenshots, the proposed fix, and the pull request.

## Run it (live mode, the default)

You need 3 things running, each in its own terminal, from the repo root:

1. **Backend.** Copy `backend/.env.example` to `backend/.env` and set `OMNISIGHT_USERNAME`, `OMNISIGHT_PASSWORD` and `OMNISIGHT_SECRET_KEY`. Then:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt && playwright install chromium
   uvicorn app.main:app --app-dir backend --port 8000
   ```
2. **Store** (the site being tested):
   ```bash
   cd app-under-test && npm install && npm run dev
   ```
3. **Dashboard:**
   ```bash
   cd dashboard && npm install && npm run dev
   ```

Open **http://localhost:5180**, sign in with the account from `backend/.env`, keep the address `http://localhost:5173`, and click **Run test**. No terminal commands are needed after that.

On Windows, activate the venv with `.venv\Scripts\activate`.

## Mock mode (no backend, no login)

```bash
VITE_DATA_SOURCE=mock npm run dev          # macOS / Linux
$env:VITE_DATA_SOURCE="mock"; npm run dev  # Windows PowerShell
```

You get 6 sample runs, labelled **Mock Data**. Starting tests is disabled in this mode.

## What a test does

1. Opens the store at 4 screen sizes (1440×900, 1280×800, 390×844, 375×667) and walks products → cart → checkout, taking 12 screenshots.
2. Finds visual defects (AI review plus a geometry check) and proposes a CSS fix.
3. Clicks every button and link at desktop size and reports ones that are covered, lead to an error page, throw an error, or possibly do nothing.
4. If **Check the fix** is ticked, applies the fix temporarily, re-captures the page, compares, and restores the file.
5. You review it under **Review & PR** and can open a pull request. CI then runs on GitHub.

## Pages

| Page | What's on it |
|---|---|
| Sign in | The reviewer login |
| Overview | Test a site, live progress, totals, recent runs, and the kinds of bugs found |
| Runs | Every run, with search and a status filter |
| Run detail | Progress tracker, then tabs: Findings, Evidence (drag the before/after slider), Fix, Review & PR, Forensics |

Use the sun/moon button to switch between dark and light. Your choice is remembered.

## Troubleshooting

| You see | Do this |
|---|---|
| "Couldn't load runs" | Start the backend on port 8000. |
| "Login not configured…" | Add the `OMNISIGHT_*` lines to `backend/.env` and restart the backend. |
| "A run is already in progress" | Wait for the current test to finish. Only one runs at a time. |
| "Host … is not in allowed target hosts" | Only the local store can be tested (`ALLOWED_TARGET_HOSTS`). |
| Sent back to sign in | Your session expired (8 hours) or the backend restarted without `OMNISIGHT_SECRET_KEY`. |

## Development

```bash
npm test        # node:test: formatting, auth, theme, lifecycle helpers
npm run build
```

| File | Role |
|---|---|
| `src/api.js` | Backend calls (with the login token) and mock data |
| `src/auth.js` | Session token and 401 handling |
| `src/theme.js` | Dark/light preference |
| `src/lifecycle.js` | Run progress steps, totals, relative times |
| `src/format.js` | Status labels, screenshot pairing, safe links |
| `src/components/` | Shell, Login, Overview, RunList, RunDetail, Evidence, CompareSlider, ReviewPanel, … |
| `vite.config.js` | Port 5180, the `/api` proxy to :8000, and `/artifacts` screenshot serving |
