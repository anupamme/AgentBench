// BUG: implicit any parameters — fails noImplicitAny under strict mode
export function createUser(data) {
  return { id: Math.random(), name: data.name, email: data.email, createdAt: new Date() };
}

export function filterUsers(users, predicate) {
  return users.filter(predicate);
}
