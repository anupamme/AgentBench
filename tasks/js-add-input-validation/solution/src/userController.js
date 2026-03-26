const users = [];

function createUser(req, res) {
  const { name, email } = req.body;
  if (!name || !email) {
    return res.status(400).json({ error: 'name and email are required' });
  }
  const user = { id: users.length + 1, name, email };
  users.push(user);
  res.status(201).json(user);
}

function getUsers(req, res) {
  res.status(200).json(users);
}

function clearUsers() {
  users.length = 0;
}

module.exports = { createUser, getUsers, clearUsers };
