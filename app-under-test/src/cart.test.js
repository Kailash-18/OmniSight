import { test } from 'node:test'
import assert from 'node:assert/strict'
import { addItem, setQty, itemCount, totalPaise, money } from './cart.js'

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
