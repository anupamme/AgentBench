'use strict';

const express = require('express');
const Book = require('../models/book');

const router = express.Router();

const ISBN_RE = /^\d{3}-\d{10}$/;

function validate(body) {
  if (!body.title || typeof body.title !== 'string' || !body.title.trim()) {
    return 'title is invalid';
  }
  if (!body.author || typeof body.author !== 'string' || !body.author.trim()) {
    return 'author is invalid';
  }
  if (!body.isbn || !ISBN_RE.test(body.isbn)) {
    return 'isbn is invalid';
  }
  if (typeof body.price !== 'number' || body.price <= 0) {
    return 'price is invalid';
  }
  return null;
}

// GET /books — list all books
router.get('/', (req, res) => {
  res.json(Book.getAll());
});

// GET /books/:id — get a single book
router.get('/:id', (req, res) => {
  const book = Book.getById(parseInt(req.params.id, 10));
  if (!book) {
    return res.status(404).json({ error: 'not found' });
  }
  res.json(book);
});

// POST /books — create a book with validation
router.post('/', (req, res) => {
  const err = validate(req.body);
  if (err) {
    return res.status(400).json({ error: err });
  }
  const { title, author, isbn, price } = req.body;
  const book = Book.add({ title, author, isbn, price });
  res.status(201).json(book);
});

module.exports = router;
