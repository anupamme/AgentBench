const db = require('../src/db');

test('connect and query', async () => {
  await db.connect();
  const rows = await db.query('SELECT * FROM users');
  expect(rows).toEqual([{ id: 1, name: 'Alice' }]);
  await db.close();
});

test('query fails when not connected', async () => {
  await expect(db.query('SELECT * FROM users')).rejects.toThrow('not connected');
});
