// Fixed catalogue: prices in paise so cart math stays exact.
export const products = [
  { id: 'mug', name: 'Stoneware Mug', blurb: 'Hand-glazed, 350 ml', price: 49900, tint: '#e9dfd3', ink: '#a0643f' },
  { id: 'tote', name: 'Linen Tote', blurb: 'Washed linen, 40 × 38 cm', price: 89900, tint: '#dfe4dc', ink: '#5d7158' },
  { id: 'lamp', name: 'Desk Lamp', blurb: 'Powder-coated steel', price: 199900, tint: '#dde2ea', ink: '#3f5a7a' },
]

export const findProduct = (id) => products.find((p) => p.id === id)
