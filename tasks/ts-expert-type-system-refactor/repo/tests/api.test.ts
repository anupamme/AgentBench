import { handleCreateUser, handleListUsers } from '../src/api';

test('creates user', () => {
  const res = handleCreateUser({ name: 'Alice', email: 'a@b.com' });
  expect((res as any).status).toBe(201);
  expect((res as any).user.name).toBe('Alice');
});

test('rejects missing fields', () => {
  const res = handleCreateUser({ name: 'Bob' });
  expect((res as any).status).toBe(400);
});

test('lists all users', () => {
  const users = [{ id: 1, name: 'Alice', email: 'a@b.com', createdAt: new Date() }];
  expect(handleListUsers(users, {})).toHaveLength(1);
});
