# everyday. — OmniSight app under test

A small mock online store that OmniSight inspects. It has a full
**Products → Cart → Checkout → Submit order → Success** journey and **three
intentional, deterministic visual defects** for the VLM to detect and repair.

Owner: Member 2. Plain React + Vite + CSS. No backend, auth, payments, or external requests.

## Install and run

Requires Node 18+ (tested on Node 24).

```bash
cd app-under-test
npm install
npm run dev          # http://localhost:5173  (port is fixed; fails instead of switching if taken)
```

From the repo root: `npm run dev --prefix app-under-test`.

| Command | What it does |
| --- | --- |
| `npm run dev` | Dev server at **http://localhost:5173** |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serves the build at **http://localhost:4173** |
| `npm test` | Cart-math smoke test (`node:test`, no extra deps) |

## Routes

All routes support direct navigation (`page.goto(...)`) in dev and preview.

| URL | Page |
| --- | --- |
| `/` | Products (3 fixed items) |
| `/cart` | Cart (empty state when nothing added) |
| `/checkout` | Checkout form, then success message after submit |

The cart lives **in memory only**. A full page load (including `goto('/checkout')`)
starts with an empty cart. Automation should add items on `/` and then use in-app links
and buttons, which navigate without a reload.

## Demo journey (manual or Playwright)

1. `/`: click **Add to cart** on Stoneware Mug twice and on Desk Lamp once.
   The header badge `cart-count` shows `3`.
2. Click **Cart** (`cart-link`). Total `cart-total` = **₹2,997**. Use +/− or **Remove** to edit.
3. Click **Continue to checkout** (`continue-to-checkout`).
4. Fill in Full name, Email (must be a valid address), and Delivery address. All are required;
   the browser blocks submission until they're valid.
5. Click **Submit order** (`submit-order`) or press Enter in a text input.
6. `order-success` appears with order number `EV-1001`, and the cart resets to 0.

Minimal Playwright (Python) path:

```python
page.goto("http://localhost:5173/")
page.get_by_test_id("add-to-cart-mug").click()
page.get_by_test_id("cart-link").click()
page.get_by_test_id("continue-to-checkout").click()
page.get_by_test_id("input-name").fill("Ada Lovelace")
page.get_by_test_id("input-email").fill("ada@example.com")
page.get_by_test_id("input-address").fill("12 Demo Street")
page.get_by_test_id("submit-order").click()
page.get_by_test_id("order-success").wait_for()
```

## Test IDs

| Area | `data-testid` |
| --- | --- |
| Header | `brand-link`, `nav-shop`, `cart-link`, `cart-count` |
| Page root (`<main>`) | `page-products`, `page-cart`, `page-checkout` |
| Products | `hero-title`, `product-list`, `product-card-{id}`, `product-price-{id}`, `add-to-cart-{id}` |
| Cart | `cart-items`, `cart-item-{id}`, `qty-{id}`, `qty-increase-{id}`, `qty-decrease-{id}`, `line-total-{id}`, `remove-{id}`, `cart-summary`, `cart-item-count`, `cart-total`, `continue-to-checkout`, `cart-empty`, `back-to-shop` |
| Checkout | `checkout-form`, `input-name`, `input-email`, `input-address`, `promo-banner`, `submit-order`, `checkout-summary`, `checkout-total`, `checkout-empty` |
| Success | `order-success`, `order-number`, `continue-shopping` |

Product ids: `mug` (₹499), `tote` (₹899), `lamp` (₹1,999). Prices are stored in paise; shown in whole rupees (en-IN).

## Viewports

Every defect reproduces at both desktop sizes and both mobile sizes:

- Desktop: **1440 × 900** and **1280 × 800** (defect-1 rule applies at ≥ 1024px)
- Mobile: **390 × 844** and **375 × 667** (defect-2 rule applies at ≤ 480px)

Kept deterministic for screenshots: no animations or transitions, system fonts only
(no web-font loading), inline SVG product art (no images to load), fixed data, and a fixed
order number. Hover styles exist, so move the mouse to the same spot (e.g. `page.mouse.move(0, 0)`)
before each screenshot if you want pixel-identical captures.

## Intentional visual defects

**These are deliberate.** They all live in [`src/styles/defects.css`](src/styles/defects.css),
loaded after `base.css`, and each one is a commented block labelled `DEFECT-n`.
`base.css` is the clean design.

- **Repair one defect:** delete its block in `defects.css`.
- **Fully repaired reference:** remove `import './styles/defects.css'` from `src/main.jsx`.
- None of them block the journey; every control stays clickable and submit still works.

| # | Name | Page / step | Viewport | Visible symptom | Cause |
| --- | --- | --- | --- | --- | --- |
| 1 | `heading-overlap` | Products `/`, on load | Desktop ≥ 1024px | Heading "Simple goods for every day." overlaps the top of the first product card (~56px overlap) | `margin-bottom: -96px` + `z-index` on `.hero-title` |
| 2 | `mobile-checkout-button-clipped` | Cart `/cart`, with ≥ 1 item | Mobile ≤ 480px | "Continue to checkout" runs past the summary card's right edge and gets cut off, arrow included (123px clipped at 390, 138px at 375) | `min-width: 460px` on `.checkout-cta` + `overflow: clip` on `.cart-summary` |
| 3 | `submit-button-obstructed` | Checkout `/checkout`, with ≥ 1 item | All | The "Free shipping" promo banner covers the Submit order button entirely; no submit button is visible | `.promo-banner` absolutely positioned over `.checkout-actions`, `pointer-events: none` |

### Reproduce

1. `npm run dev`
2. Defect 1: open `http://localhost:5173/` at 1440×900 or 1280×800.
3. Defect 2: resize to 390×844 or 375×667, add any product, open Cart.
4. Defect 3: at any size, add a product, go Cart → Continue to checkout.

### Notes for automation

- Defect 3 uses `pointer-events: none`, so Playwright's `click()` on `submit-order`
  **succeeds** (its hit-target check passes), and so does `document.elementFromPoint`.
  This is intentional: only a visual check catches it, which is what OmniSight is for.
  To detect it in the DOM, compare the bounding boxes of `promo-banner` and `submit-order`.
- Defect 2 uses `overflow: clip` instead of `hidden`, so the card isn't a scroll container
  and Playwright's scroll-into-view can't shift its contents between runs.
- Patch allowlist suggestion: `app-under-test/src/styles/defects.css` (and maybe `base.css`).
