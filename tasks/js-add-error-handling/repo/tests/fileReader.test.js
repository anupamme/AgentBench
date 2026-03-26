const path = require('path');
const { readConfig } = require('../src/fileReader');

test('reads valid config file', () => {
  const config = readConfig(path.join(__dirname, 'fixtures/valid.json'));
  expect(config).toEqual({ debug: true, port: 3000 });
});

test('returns null on missing file', () => {
  const result = readConfig('/nonexistent/path/config.json');
  expect(result).toBeNull();
});
