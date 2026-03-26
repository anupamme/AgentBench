let inventoryUpdated = false;

async function validatePayment(orderId) {
  return { orderId, valid: true };
}

async function updateInventory(orderId) {
  inventoryUpdated = true;
  return { orderId, updated: true };
}

async function processOrder(orderId) {
  const payment = await validatePayment(orderId);
  if (!payment.valid) throw new Error('Payment failed');
  updateInventory(orderId); // BUG: missing await
  return { orderId, status: 'complete' };
}

function getInventoryState() { return inventoryUpdated; }
function resetInventory() { inventoryUpdated = false; }

module.exports = { processOrder, getInventoryState, resetInventory };
