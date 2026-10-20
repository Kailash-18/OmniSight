import { useEffect, useState } from 'react'
import { addItem, setQty, itemCount } from './cart.js'
import ProductList from './components/ProductList.jsx'
import Cart from './components/Cart.jsx'
import Checkout from './components/Checkout.jsx'

// ponytail: three fixed routes, so a pushState switch replaces a router library.
const routes = { '/': ProductList, '/cart': Cart, '/checkout': Checkout }

export default function App() {
  const [path, setPath] = useState(window.location.pathname)
  const [cart, setCart] = useState({})

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const navigate = (to) => {
    window.history.pushState(null, '', to)
    setPath(to)
    window.scrollTo(0, 0)
  }

  // Plain left-clicks route in-app; real hrefs keep direct navigation and new tabs working.
  const link = (to) => ({
    href: to,
    onClick: (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
      e.preventDefault()
      navigate(to)
    },
  })

  const Page = routes[path] || ProductList
  const count = itemCount(cart)

  return (
    <>
      <header className="site-header">
        <div className="container header-inner">
          <a className="brand" data-testid="brand-link" {...link('/')}>everyday.</a>
          <nav aria-label="Main">
            <a className="nav-link" data-testid="nav-shop" {...link('/')}>Shop</a>
            <a className="nav-link cart-link" data-testid="cart-link" aria-label={`Cart, ${count} items`} {...link('/cart')}>
              Cart <span className="cart-badge" data-testid="cart-count">{count}</span>
            </a>
          </nav>
        </div>
      </header>
      <main className="container page" data-testid={`page-${path === '/' ? 'products' : path.slice(1)}`}>
        <Page
          cart={cart}
          link={link}
          navigate={navigate}
          onAdd={(id) => setCart((c) => addItem(c, id))}
          onQty={(id, q) => setCart((c) => setQty(c, id, q))}
          onClear={() => setCart({})}
        />
      </main>
      <footer className="site-footer">
        <div className="container">everyday. is a demo store for OmniSight. No real orders or payments.</div>
      </footer>
    </>
  )
}
