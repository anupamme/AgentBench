'use strict';

const express = require('express');
const booksRouter = require('./routes/books');

const app = express();

app.use(express.json());
app.use('/books', booksRouter);

module.exports = app;

if (require.main === module) {
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => {
    console.log(`Bookstore API listening on port ${PORT}`);
  });
}
