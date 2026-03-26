import { parseConfig, mergeConfigs, getTag } from '../src/config';

test('parseConfig with all fields', () => {
  const result = parseConfig({ host: 'example.com', port: '8080', debug: true, tags: ['a'] });
  expect(result.host).toBe('example.com');
  expect(result.port).toBe(8080);
  expect(result.debug).toBe(true);
  expect(result.tags).toEqual(['a']);
});

test('parseConfig with defaults', () => {
  const result = parseConfig({});
  expect(result.host).toBe('localhost');
  expect(result.port).toBe(3000);
});

test('mergeConfigs', () => {
  const base = { host: 'a', port: 1, debug: false, tags: [] };
  const merged = mergeConfigs(base, { port: 2 });
  expect(merged.port).toBe(2);
  expect(merged.host).toBe('a');
});

test('getTag', () => {
  const cfg = parseConfig({ tags: ['x', 'y'] });
  expect(getTag(cfg, 0)).toBe('x');
});
