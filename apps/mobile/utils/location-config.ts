const _env = (globalThis as { process?: { env?: Record<string, string | undefined> } })
  .process?.env ?? {};

export const DEFAULT_DISCOVERY_LAT    = parseFloat(_env.EXPO_PUBLIC_DEFAULT_LAT       ?? '37.9838');
export const DEFAULT_DISCOVERY_LNG    = parseFloat(_env.EXPO_PUBLIC_DEFAULT_LNG       ?? '23.7275');
export const DEFAULT_DISCOVERY_RADIUS = parseFloat(_env.EXPO_PUBLIC_DEFAULT_RADIUS_KM ?? '50');
