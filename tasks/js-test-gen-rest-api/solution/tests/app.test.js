const { makeRequest, reset } = require('../src/app');

beforeEach(() => reset());

describe('GET /users', () => {
  test('returns empty array initially', () => {
    const res = makeRequest('GET', '/users');
    expect(res._status).toBe(200);
    expect(res._body).toEqual([]);
  });

  test('returns created users', () => {
    makeRequest('POST', '/users', { name: 'Alice', email: 'a@b.com' });
    const res = makeRequest('GET', '/users');
    expect(res._body).toHaveLength(1);
    expect(res._body[0].name).toBe('Alice');
  });
});

describe('POST /users', () => {
  test('creates user with valid data', () => {
    const res = makeRequest('POST', '/users', { name: 'Bob', email: 'b@c.com' });
    expect(res._status).toBe(201);
    expect(res._body).toMatchObject({ name: 'Bob', email: 'b@c.com' });
    expect(res._body.id).toBeDefined();
  });

  test('returns 400 when name missing', () => {
    const res = makeRequest('POST', '/users', { email: 'x@y.com' });
    expect(res._status).toBe(400);
  });

  test('returns 400 when email missing', () => {
    const res = makeRequest('POST', '/users', { name: 'Alice' });
    expect(res._status).toBe(400);
  });
});

describe('DELETE /users/:id', () => {
  test('deletes existing user', () => {
    makeRequest('POST', '/users', { name: 'Carol', email: 'c@d.com' });
    const listRes = makeRequest('GET', '/users');
    const id = listRes._body[0].id;
    const res = makeRequest('DELETE', `/users/${id}`);
    expect(res._status).toBe(204);
    expect(makeRequest('GET', '/users')._body).toHaveLength(0);
  });

  test('returns 404 for non-existent user', () => {
    const res = makeRequest('DELETE', '/users/9999');
    expect(res._status).toBe(404);
  });
});
