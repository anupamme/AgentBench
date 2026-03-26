const DARK_MODE = false;
const NEW_DASHBOARD = true;

function getTheme() {
  return DARK_MODE ? 'dark' : 'light';
}

function getDashboardVersion() {
  return NEW_DASHBOARD ? 'v2' : 'v1';
}

module.exports = { getTheme, getDashboardVersion };
