function createApp() {
  const routes = [];

  function get(path, ...handlers) {
    routes.push({ method: 'GET', path, handlers });
  }

  function handle(method, path, body) {
    const route = routes.find(r => r.method === method && r.path === path);
    if (!route) return { status: 404, body: { error: 'not found' } };
    let result = null;
    const req = { method, path, headers: body.headers || {}, body };
    const res = {
      _status: 200,
      status(code) { this._status = code; return this; },
      json(data) { result = { status: this._status, body: data }; },
    };
    let i = 0;
    function next() {
      const handler = route.handlers[i++];
      if (handler) handler(req, res, next);
    }
    next();
    return result;
  }

  get('/data', (req, res) => {
    res.status(200).json({ items: ['a', 'b', 'c'] });
  });

  return { handle };
}

module.exports = { createApp };
