import { createUser, filterUsers } from './models';

export function handleCreateUser(body: any): any {
  if (!body.name || !body.email) return { error: 'missing fields', status: 400 };
  const user = createUser(body);
  return { user, status: 201 };
}

export function handleListUsers(users: any[], query: any): any {
  if (query.name) return filterUsers(users, (u: any) => u.name === query.name);
  return users;
}
