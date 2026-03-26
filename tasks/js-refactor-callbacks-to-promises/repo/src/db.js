let _connected = false;
let _data = { users: [{ id: 1, name: 'Alice' }] };

function connect(callback) {
  setTimeout(() => {
    _connected = true;
    callback(null, { connected: true });
  }, 0);
}

function query(sql, callback) {
  setTimeout(() => {
    if (!_connected) return callback(new Error('not connected'));
    if (sql.includes('users')) return callback(null, _data.users);
    callback(null, []);
  }, 0);
}

function close(callback) {
  setTimeout(() => {
    _connected = false;
    callback(null);
  }, 0);
}

module.exports = { connect, query, close };
