export interface User {
  id: number;
  name: string;
  email: string;
  createdAt: Date;
}

export interface UserData {
  name: string;
  email: string;
}

export function createUser(data: UserData): User {
  return { id: Math.random(), name: data.name, email: data.email, createdAt: new Date() };
}

export function filterUsers(users: User[], predicate: (u: User) => boolean): User[] {
  return users.filter(predicate);
}
