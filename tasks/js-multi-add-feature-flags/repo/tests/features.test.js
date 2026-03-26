const { FeatureFlags } = require('../src/features');
const { getTheme, getDashboardVersion } = require('../src/app');

test('isEnabled returns false for unknown flag', () => {
  const ff = new FeatureFlags();
  expect(ff.isEnabled('unknown')).toBe(false);
});

test('isEnabled returns true for enabled flag', () => {
  const ff = new FeatureFlags({ new_dashboard: true });
  expect(ff.isEnabled('new_dashboard')).toBe(true);
});

test('override changes flag value', () => {
  const ff = new FeatureFlags({ dark_mode: false });
  ff.override('dark_mode', true);
  expect(ff.isEnabled('dark_mode')).toBe(true);
});

test('getTheme returns a string', () => {
  expect(typeof getTheme()).toBe('string');
});

test('getDashboardVersion returns v1 or v2', () => {
  expect(['v1', 'v2']).toContain(getDashboardVersion());
});
