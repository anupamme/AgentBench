const users = [];
let nextId = 1;

function makeRequest(method, path, body) {
  const req = { method, path, body: body || {}, params: {} };
  const idMatch = path.match(/\/users\/(\d+)/);
  if (idMatch) req.params.id = idMatch[1];
  const res = { _status: 200, _body: null };
  res.status = (code) => { res._status = code; return res; };
  res.json = (data) => { res._body = data; return res; };

  if (method === 'GET' && path === '/users') {
    getUsers(req, res);
  } else if (method === 'POST' && path === '/users') {
    createUser(req, res);
  } else if (method === 'DELETE' && path.startsWith('/users/')) {
    deleteUser(req, res);
  }
  return res;
}

function getUsers(req, res) {
  res.status(200).json([...users]);
}

function createUser(req, res) {
  const { name, email } = req.body;
  if (!name || !email) return res.status(400).json({ error: 'name and email required' });
  const user = { id: nextId++, name, email };
  users.push(user);
  res.status(201).json(user);
}

function deleteUser(req, res) {
  const id = parseInt(req.params.id);
  const idx = users.findIndex(u => u.id === id);
  if (idx === -1) return res.status(404).json({ error: 'not found' });
  users.splice(idx, 1);
  res.status(204).json({});
}

function reset() { users.length = 0; nextId = 1; }

module.exports = { makeRequest, getUsers, createUser, deleteUser, reset };
