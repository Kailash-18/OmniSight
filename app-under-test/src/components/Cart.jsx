import { findProduct } from '../data/products.js'
import { itemCount, totalPaise, money } from '../cart.js'

export default function Cart({ cart, onQty, link, navigate }) {
  const ids = Object.keys(cart)

  if (ids.length === 0) {
    return (
      <section className="empty card" data-testid="cart-empty">
        <h1>Your cart is empty</h1>
        <p className="muted">Pick something you'll use every day.</p>
        <a className="btn btn-primary" data-testid="back-to-shop" {...link('/')}>Browse products</a>
      </section>
    )
  }

  return (
    <section className="two-col">
      <div>
        <h1>Your cart</h1>
        <ul className="line-items" data-testid="cart-items">
          {ids.map((id) => {
            const p = findProduct(id)
            const q = cart[id]
            return (
              <li key={id} className="card line-item" data-testid={`cart-item-${id}`}>
                <div className="line-info">
                  <h2 className="product-name">{p.name}</h2>
                  <p className="muted">{money(p.price)} each</p>
                </div>
                <div className="qty" role="group" aria-label={`Quantity for ${p.name}`}>
                  <button type="button" className="qty-btn" data-testid={`qty-decrease-${id}`} aria-label={`Decrease ${p.name}`} onClick={() => onQty(id, q - 1)}>−</button>
                  <output data-testid={`qty-${id}`} aria-live="polite">{q}</output>
                  <button type="button" className="qty-btn" data-testid={`qty-increase-${id}`} aria-label={`Increase ${p.name}`} onClick={() => onQty(id, q + 1)}>+</button>
                </div>
                <p className="line-total" data-testid={`line-total-${id}`}>{money(p.price * q)}</p>
                <button type="button" className="link-btn" data-testid={`remove-${id}`} onClick={() => onQty(id, 0)}>Remove</button>
              </li>
            )
          })}
        </ul>
      </div>
      <aside className="card summary cart-summary" data-testid="cart-summary" aria-label="Order summary">
        <h2>Summary</h2>
        <dl className="summary-rows">
          <dt>Items</dt><dd data-testid="cart-item-count">{itemCount(cart)}</dd>
          <dt>Shipping</dt><dd>Free</dd>
          <dt className="total">Total</dt><dd className="total" data-testid="cart-total">{money(totalPaise(cart))}</dd>
        </dl>
        <button type="button" className="btn btn-primary btn-block checkout-cta" data-testid="continue-to-checkout" onClick={() => navigate('/checkout')}>
          Continue to checkout <span aria-hidden="true">→</span>
        </button>
      </aside>
    </section>
  )
}
