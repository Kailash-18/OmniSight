// Pure cart helpers. Cart shape: { [productId]: quantity }.
import { findProduct } from './data/products.js'

export const addItem = (cart, id) => ({ ...cart, [id]: (cart[id] || 0) + 1 })

export const setQty = (cart, id, qty) => {
  const next = { ...cart }
  if (qty > 0) next[id] = qty
  else delete next[id]
  return next
}

export const itemCount = (cart) => Object.values(cart).reduce((n, q) => n + q, 0)

export const totalPaise = (cart) =>
  Object.entries(cart).reduce((sum, [id, q]) => sum + findProduct(id).price * q, 0)

const fmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
export const money = (paise) => fmt.format(paise / 100)

// `required` accepts a field of only spaces, so checkout re-checks the trimmed values.
export const blankFields = (data, names) => names.filter((n) => !String(data[n] ?? '').trim())

// Order numbers count up per page load (demo store, nothing is stored).
let lastOrder = 1000
export const nextOrderNumber = () => `EV-${++lastOrder}`
