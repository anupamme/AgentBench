'use strict';

let books = [];
let nextId = 1;

function add(data) {
  const book = { id: nextId++, ...data };
  books.push(book);
  return book;
}

function getAll() {
  return [...books];
}

function getById(id) {
  return books.find((b) => b.id === id) || null;
}

function reset() {
  books = [];
  nextId = 1;
}

module.exports = { add, getAll, getById, reset };
