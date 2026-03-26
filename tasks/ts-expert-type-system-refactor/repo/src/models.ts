export function createUser(data: any): any {
  return { id: Math.random(), name: data.name, email: data.email, createdAt: new Date() };
}

export function filterUsers(users: any[], predicate: any): any[] {
  return users.filter(predicate);
}
