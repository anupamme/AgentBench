async function fetchUser(userId) {
  const response = await fetch(`https://api.example.com/users/${userId}`);
  const data = await response.json();
  return data;
}

async function fetchUserName(userId) {
  const user = await fetchUser(userId);
  return user ? user.name : null;
}

module.exports = { fetchUser, fetchUserName };
