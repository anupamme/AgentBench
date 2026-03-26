const jwt = require('jsonwebtoken');
const { createApp } = require('../src/app');

const SECRET = 'test-secret';
function makeToken(payload = { user: 'alice' }, secret = SECRET) {
  return jwt.sign(payload, secret);
}

test('returns 401 when no Authorization header', () => {
  const app = createApp();
  const res = app.handle('GET', '/data', { headers: {} });
  expect(res.status).toBe(401);
});

test('returns 403 for invalid token', () => {
  const app = createApp();
  const res = app.handle('GET', '/data', { headers: { authorization: 'Bearer invalid' } });
  expect(res.status).toBe(403);
});

test('returns 200 for valid token', () => {
  const app = createApp();
  const token = makeToken();
  const res = app.handle('GET', '/data', { headers: { authorization: `Bearer ${token}` } });
  expect(res.status).toBe(200);
  expect(res.body.items).toEqual(['a', 'b', 'c']);
});

test('returns 403 for wrong secret', () => {
  const app = createApp();
  const token = makeToken({ user: 'eve' }, 'wrong-secret');
  const res = app.handle('GET', '/data', { headers: { authorization: `Bearer ${token}` } });
  expect(res.status).toBe(403);
});
