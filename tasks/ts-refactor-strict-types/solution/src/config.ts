export interface AppConfig {
  host: string;
  port: number;
  debug: boolean;
  tags: string[];
}

export interface RawConfig {
  host?: string;
  port?: string | number;
  debug?: boolean;
  tags?: string[];
}

export function parseConfig(raw: RawConfig): AppConfig {
  return {
    host: raw.host ?? 'localhost',
    port: Number(raw.port) || 3000,
    debug: Boolean(raw.debug),
    tags: Array.isArray(raw.tags) ? raw.tags : [],
  };
}

export function mergeConfigs(base: AppConfig, override: Partial<AppConfig>): AppConfig {
  return { ...base, ...override };
}

export function getTag(config: AppConfig, index: number): string {
  return config.tags[index];
}
