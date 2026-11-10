import { test } from 'node:test'
import assert from 'node:assert/strict'
import { addItem, setQty, itemCount, totalPaise, money, blankFields, nextOrderNumber } from './cart.js'

test('cart math', () => {
  let cart = {}
  assert.equal(itemCount(cart), 0)
  assert.equal(totalPaise(cart), 0)

  cart = addItem(addItem(addItem(cart, 'mug'), 'mug'), 'lamp')
  assert.deepEqual(cart, { mug: 2, lamp: 1 })
  assert.equal(itemCount(cart), 3)
  assert.equal(totalPaise(cart), 2 * 49900 + 199900)
  assert.equal(money(totalPaise(cart)), '₹2,997')
  assert.equal(money(12345600), '₹1,23,456') // Indian lakh grouping

  cart = setQty(cart, 'mug', 5)
  assert.equal(totalPaise(cart), 5 * 49900 + 199900)

  cart = setQty(cart, 'lamp', 0) // removing
  assert.deepEqual(cart, { mug: 5 })
  assert.equal(itemCount(cart), 5)
})

test('blankFields names required fields that are empty or only spaces', () => {
  assert.deepEqual(blankFields({ name: '  ', email: 'a@b.co', address: '\n\t' }, ['name', 'address']), ['name', 'address'])
  assert.deepEqual(blankFields({ name: 'Asha', address: '1 Main St' }, ['name', 'address']), [])
})

test('nextOrderNumber counts up from EV-1001', () => {
  const a = nextOrderNumber()
  const b = nextOrderNumber()
  assert.match(a, /^EV-\d{4}$/)
  assert.equal(Number(b.slice(3)), Number(a.slice(3)) + 1)
})
