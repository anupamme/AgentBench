const { getAge, getName } = require('../src/user');

test('returns age when profile exists', () => {
  const user = { name: 'Alice', profile: { age: 30 } };
  expect(getAge(user)).toBe(30);
});

test('returns null for missing profile', () => {
  const user = { name: 'Bob' };
  expect(getAge(user)).toBeNull();
});

test('returns null for null profile', () => {
  const user = { name: 'Carol', profile: null };
  expect(getAge(user)).toBeNull();
});

test('getName returns name', () => {
  expect(getName({ name: 'Dave' })).toBe('Dave');
});
