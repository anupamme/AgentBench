const { createUser, getUsers, clearUsers } = require('../src/userController');

function makeReq(body) { return { body }; }
function makeRes() {
  const res = {};
  res.status = jest.fn().mockReturnValue(res);
  res.json = jest.fn().mockReturnValue(res);
  return res;
}

beforeEach(() => clearUsers());

test('creates user with valid data', () => {
  const res = makeRes();
  createUser(makeReq({ name: 'Alice', email: 'a@b.com' }), res);
  expect(res.status).toHaveBeenCalledWith(201);
  expect(res.json).toHaveBeenCalledWith(expect.objectContaining({ name: 'Alice' }));
});

test('returns 400 when name is missing', () => {
  const res = makeRes();
  createUser(makeReq({ email: 'a@b.com' }), res);
  expect(res.status).toHaveBeenCalledWith(400);
});

test('returns 400 when email is missing', () => {
  const res = makeRes();
  createUser(makeReq({ name: 'Alice' }), res);
  expect(res.status).toHaveBeenCalledWith(400);
});

test('returns 400 when body is empty', () => {
  const res = makeRes();
  createUser(makeReq({}), res);
  expect(res.status).toHaveBeenCalledWith(400);
});
