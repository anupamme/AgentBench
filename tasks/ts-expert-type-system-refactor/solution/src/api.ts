import { createUser, filterUsers, User } from './models';

interface CreateResponse { user: User; status: number; }
interface ErrorResponse { error: string; status: number; }

export function handleCreateUser(body: Record<string, unknown>): CreateResponse | ErrorResponse {
  if (!body.name || !body.email) return { error: 'missing fields', status: 400 };
  const user = createUser({ name: String(body.name), email: String(body.email) });
  return { user, status: 201 };
}

export function handleListUsers(users: User[], query: Record<string, unknown>): User[] {
  if (query.name) return filterUsers(users, (u) => u.name === String(query.name));
  return users;
}
