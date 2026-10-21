import { products } from '../data/products.js'
import { money } from '../cart.js'
import ProductArt from './ProductArt.jsx'

export default function ProductList({ onAdd, cart }) {
  return (
    <section aria-labelledby="hero-title">
      <div className="hero">
        <p className="eyebrow">The autumn edit</p>
        <h1 id="hero-title" className="hero-title" data-testid="hero-title">Simple goods for every day.</h1>
      </div>
      <ul className="product-grid" data-testid="product-list">
        {products.map((p) => (
          <li key={p.id} className="card product-card" data-testid={`product-card-${p.id}`}>
            <ProductArt product={p} />
            <div className="product-body">
              <div>
                <h2 className="product-name">{p.name}</h2>
                <p className="muted">{p.blurb}</p>
              </div>
              <p className="price" data-testid={`product-price-${p.id}`}>{money(p.price)}</p>
            </div>
            <button type="button" className="btn btn-primary" data-testid={`add-to-cart-${p.id}`} onClick={() => onAdd(p.id)}>
              Add to cart{cart[p.id] ? ` (${cart[p.id]})` : ''}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
