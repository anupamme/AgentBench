'use strict';

const request = require('supertest');
const app = require('../src/app');
const Book = require('../src/models/book');

beforeEach(() => {
  Book.reset();
});

describe('GET /books', () => {
  it('returns empty array initially', async () => {
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });
});

describe('POST /books — happy path', () => {
  it('creates a book with valid data', async () => {
    const res = await request(app).post('/books').send({
      title: 'Clean Code',
      author: 'Robert C. Martin',
      isbn: '978-0132350884',
      price: 35.99,
    });
    expect(res.status).toBe(201);
    expect(res.body.id).toBe(1);
    expect(res.body.title).toBe('Clean Code');
  });
});

describe('GET /books/:id', () => {
  it('returns a book by id', async () => {
    await request(app).post('/books').send({
      title: 'The Pragmatic Programmer',
      author: 'David Thomas',
      isbn: '978-0135957059',
      price: 49.95,
    });
    const res = await request(app).get('/books/1');
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('The Pragmatic Programmer');
  });

  it('returns 404 for unknown id', async () => {
    const res = await request(app).get('/books/999');
    expect(res.status).toBe(404);
  });
});

describe('POST /books — validation', () => {
  it('rejects missing title', async () => {
    const res = await request(app).post('/books').send({
      author: 'Someone',
      isbn: '978-0132350884',
      price: 10,
    });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/title/i);
  });

  it('rejects missing author', async () => {
    const res = await request(app).post('/books').send({
      title: 'A Book',
      isbn: '978-0132350884',
      price: 10,
    });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/author/i);
  });

  it('rejects invalid isbn format', async () => {
    const res = await request(app).post('/books').send({
      title: 'A Book',
      author: 'Someone',
      isbn: 'not-an-isbn',
      price: 10,
    });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/isbn/i);
  });

  it('rejects non-positive price', async () => {
    const res = await request(app).post('/books').send({
      title: 'A Book',
      author: 'Someone',
      isbn: '978-0132350884',
      price: -5,
    });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/price/i);
  });

  it('rejects zero price', async () => {
    const res = await request(app).post('/books').send({
      title: 'A Book',
      author: 'Someone',
      isbn: '978-0132350884',
      price: 0,
    });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/price/i);
  });
});
