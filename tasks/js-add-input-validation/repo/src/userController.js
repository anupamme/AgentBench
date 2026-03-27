const users = [];

function createUser(req, res) {
  const { name, email } = req.body;
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
