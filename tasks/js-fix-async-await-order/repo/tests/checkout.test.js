const { processOrder, getInventoryState, resetInventory } = require('../src/checkout');

beforeEach(() => resetInventory());

test('order processes successfully', async () => {
  const result = await processOrder('order-1');
  expect(result.status).toBe('complete');
});

test('inventory updated before return', async () => {
  await processOrder('order-2');
  expect(getInventoryState()).toBe(true);
});
