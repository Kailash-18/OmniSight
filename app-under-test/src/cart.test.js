import { test } from 'node:test'
import assert from 'node:assert/strict'
import { addItem, setQty, itemCount, totalCents, money } from './cart.js'

test('cart math', () => {
  let cart = {}
  assert.equal(itemCount(cart), 0)
  assert.equal(totalCents(cart), 0)

  cart = addItem(addItem(addItem(cart, 'mug'), 'mug'), 'lamp')
  assert.deepEqual(cart, { mug: 2, lamp: 1 })
  assert.equal(itemCount(cart), 3)
  assert.equal(totalCents(cart), 2 * 2400 + 6400)
  assert.equal(money(totalCents(cart)), '$112.00')

  cart = setQty(cart, 'mug', 5)
  assert.equal(totalCents(cart), 5 * 2400 + 6400)

  cart = setQty(cart, 'lamp', 0) // removing
  assert.deepEqual(cart, { mug: 5 })
  assert.equal(itemCount(cart), 5)
})
