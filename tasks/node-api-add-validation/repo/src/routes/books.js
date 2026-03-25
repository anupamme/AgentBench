'use strict';

const express = require('express');
const Book = require('../models/book');

const router = express.Router();

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

// POST /books — create a book (no validation yet)
router.post('/', (req, res) => {
  const { title, author, isbn, price } = req.body;
  const book = Book.add({ title, author, isbn, price });
  res.status(201).json(book);
});

module.exports = router;
