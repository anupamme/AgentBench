export function parseConfig(raw: any): any {
  return {
    host: raw.host || 'localhost',
    port: Number(raw.port) || 3000,
    debug: Boolean(raw.debug),
    tags: Array.isArray(raw.tags) ? raw.tags : [],
  };
}

export function mergeConfigs(base: any, override: any): any {
  return { ...base, ...override };
}

export function getTag(config: any, index: any): any {
  return config.tags[index];
}
