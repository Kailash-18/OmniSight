import { useState } from 'react'
import { findProduct } from '../data/products.js'
import { itemCount, totalCents, money } from '../cart.js'

export default function Checkout({ cart, link, onClear }) {
  const [placed, setPlaced] = useState(null)

  if (placed) {
    return (
      <section className="empty card" data-testid="order-success" role="status">
        <h1>Thank you, {placed.name}!</h1>
        <p>Your demo order <strong data-testid="order-number">EV-1001</strong> for {placed.total} is confirmed.</p>
        <p className="muted">A confirmation would be sent to {placed.email}. (Demo only, nothing was charged.)</p>
        <a className="btn btn-primary" data-testid="continue-shopping" {...link('/')}>Continue shopping</a>
      </section>
    )
  }

  if (itemCount(cart) === 0) {
    return (
      <section className="empty card" data-testid="checkout-empty">
        <h1>Nothing to check out</h1>
        <p className="muted">Add a product to your cart first.</p>
        <a className="btn btn-primary" data-testid="back-to-shop" {...link('/')}>Browse products</a>
      </section>
    )
  }

  // Native required/type validation blocks invalid submits before this runs.
  const submit = (e) => {
    e.preventDefault()
    const data = Object.fromEntries(new FormData(e.currentTarget))
    setPlaced({ name: data.name.trim(), email: data.email, total: money(totalCents(cart)) })
    onClear()
  }

  return (
    <section className="two-col">
      <form className="card checkout-form" data-testid="checkout-form" onSubmit={submit} aria-labelledby="checkout-title">
        <h1 id="checkout-title">Checkout</h1>
        <label className="field">
          <span>Full name</span>
          <input name="name" type="text" autoComplete="name" required data-testid="input-name" />
        </label>
        <label className="field">
          <span>Email</span>
          <input name="email" type="email" autoComplete="email" required data-testid="input-email" />
        </label>
        <label className="field">
          <span>Delivery address</span>
          <textarea name="address" rows="3" autoComplete="street-address" required data-testid="input-address" />
        </label>
        <div className="checkout-actions">
          <p className="promo-banner" data-testid="promo-banner">Free shipping on every order — no code needed.</p>
          <button type="submit" className="btn btn-primary btn-block" data-testid="submit-order">Submit order</button>
        </div>
      </form>
      <aside className="card summary" data-testid="checkout-summary" aria-label="Order summary">
        <h2>Your order</h2>
        <ul className="summary-lines">
          {Object.entries(cart).map(([id, q]) => (
            <li key={id}><span>{findProduct(id).name} × {q}</span><span>{money(findProduct(id).price * q)}</span></li>
          ))}
        </ul>
        <dl className="summary-rows">
          <dt className="total">Total</dt><dd className="total" data-testid="checkout-total">{money(totalCents(cart))}</dd>
        </dl>
      </aside>
    </section>
  )
}
