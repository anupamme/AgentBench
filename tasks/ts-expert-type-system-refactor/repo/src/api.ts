import { createUser, filterUsers } from './models';

// BUG: implicit any parameters — fails noImplicitAny under strict mode
export function handleCreateUser(body) {
  if (!body.name || !body.email) return { error: 'missing fields', status: 400 };
  const user = createUser(body);
  return { user, status: 201 };
}

export function handleListUsers(users, query) {
  if (query.name) return filterUsers(users, u => u.name === query.name);
  return users;
}
