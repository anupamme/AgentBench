async function fetchUser(userId) {
  try {
    const response = await fetch(`https://api.example.com/users/${userId}`);
    const data = await response.json();
    return data;
  } catch (e) {
    return null;
  }
}

async function fetchUserName(userId) {
  const user = await fetchUser(userId);
  return user ? user.name : null;
}

module.exports = { fetchUser, fetchUserName };
