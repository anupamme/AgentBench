const { fetchUser } = require('../src/api');

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.resetAllMocks();
});

test('returns user data on success', async () => {
  global.fetch.mockResolvedValue({
    json: jest.fn().mockResolvedValue({ id: 1, name: 'Alice' }),
  });
  const user = await fetchUser(1);
  expect(user).toEqual({ id: 1, name: 'Alice' });
});

test('returns null on fetch failure', async () => {
  global.fetch.mockRejectedValue(new Error('Network error'));
  const user = await fetchUser(1);
  expect(user).toBeNull();
});
