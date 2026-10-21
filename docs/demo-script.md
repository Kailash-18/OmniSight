# OmniSight End-to-End Demonstration Script

This document provides the step-by-step walkthrough for demonstrating the OmniSight closed remediation loop during technical reviews and project evaluations.

---

## Prerequisites
1. **Mock Store**: Running locally on `http://localhost:5173`.
   ```bash
   npm run dev --prefix app-under-test
   ```
2. **Backend Gateway**: Running locally on `http://localhost:8000`.
   ```bash
   uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
3. **Environment**: Python virtual environment activated with `playwright` installed.

---

## The 9-Step Demonstration Workflow

### Step 1: Baseline Inspection
* Open `http://localhost:5173` on desktop ($1440\times900$) and mobile ($375\times667$).
* Point out the deliberate visual defects:
  * **Products Page (`/`)**: Hero heading overlaps product cards on desktop.
  * **Cart Page (`/cart`)**: "Continue to checkout" button is clipped on mobile viewports.
  * **Checkout Page (`/checkout`)**: Submit order button is obstructed by the free shipping banner.

### Step 2: Triggering the Audit Run
* Trigger a run via CLI or simulated webhook:
  ```bash
  python -m automation.cli --target http://localhost:5173 --scenario checkout_flow
  ```
* Observe run initialization, viewport setup, and session allocation.

### Step 3: Browser Navigation & Multi-Page Evidence
* Playwright automates the complete flow:
  1. Loads `/` and saves `desktop_1440x900_home.png`.
  2. Adds item to cart with stable test ID `add-to-cart-mug`.
  3. Navigates to `/cart` and saves `mobile_375x667_cart.png`.
  4. Continues to `/checkout` and captures `desktop_1280x800_checkout.png`.
  5. Extracts DOM tree snapshots, bounding boxes, and console errors into `artifacts/runs/<run-id>/`.

### Step 4: Multimodal VLM Audit
* Multimodal VLM receives screenshots alongside DOM context.
* Returns structured finding in JSON format with defect category, bounding coordinates, and confidence score.

### Step 5: Patch Security Validation
* The backend patch validator inspects the proposed CSS diff:
  * Verifies target file is within `app-under-test/src/styles/`.
  * Verifies no path traversal (`..`), absolute paths, or JavaScript injections.

### Step 6: Isolated Sandbox Retest
* The patch is applied in an isolated workspace.
* Playwright reruns the exact scenario to capture `after.png`.

### Step 7: Verification & Remediation Check
* Automated comparison confirms the defect is resolved without introducing secondary visual regressions.

### Step 8: Automated GitHub Pull Request
* PyGithub creates a fix branch: `omnisight-fix-<run-id>`.
* Commits the patch and opens a Pull Request with before/after visual proof, DOM evidence, and explanation.

### Step 9: Human Review & Oversight
* Reviewer inspects the Pull Request or React QA Dashboard to give final approval for merging.
