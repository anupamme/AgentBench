// BUG: parameters have no type annotations → implicit any, fails noImplicitAny
export function parseConfig(raw) {
  return {
    host: raw.host || 'localhost',
    port: Number(raw.port) || 3000,
    debug: Boolean(raw.debug),
    tags: Array.isArray(raw.tags) ? raw.tags : [],
  };
}

export function mergeConfigs(base, override) {
  return { ...base, ...override };
}

export function getTag(config, index) {
  return config.tags[index];
}
