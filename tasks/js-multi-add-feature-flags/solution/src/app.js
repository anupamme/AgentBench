const { FeatureFlags } = require('./features');

const flags = new FeatureFlags({ dark_mode: false, new_dashboard: true });

function getTheme() {
  return flags.isEnabled('dark_mode') ? 'dark' : 'light';
}

function getDashboardVersion() {
  return flags.isEnabled('new_dashboard') ? 'v2' : 'v1';
}

module.exports = { getTheme, getDashboardVersion, flags };
