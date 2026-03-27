const jwt = require('jsonwebtoken');
const SECRET = 'test-secret';

function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization || req.headers.Authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'missing token' });
  }
  const token = authHeader.split(' ')[1];
  try {
    jwt.verify(token, SECRET);
    next();
  } catch (e) {
    res.status(403).json({ error: 'invalid token' });
  }
}

module.exports = { authMiddleware };
