let _connected = false;
let _data = { users: [{ id: 1, name: 'Alice' }] };

function connect() {
  return new Promise((resolve) => {
    setTimeout(() => {
      _connected = true;
      resolve({ connected: true });
    }, 0);
  });
}

function query(sql) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (!_connected) return reject(new Error('not connected'));
      if (sql.includes('users')) return resolve(_data.users);
      resolve([]);
    }, 0);
  });
}

function close() {
  return new Promise((resolve) => {
    setTimeout(() => {
      _connected = false;
      resolve();
    }, 0);
  });
}

module.exports = { connect, query, close };
