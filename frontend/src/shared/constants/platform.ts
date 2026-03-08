/**
 * Unified platform constants — single source of truth.
 *
 * Replaces per-page PLATFORM_LABELS / PLATFORM_SHORT / PLATFORM_TAG /
 * PLATFORM_COLORS duplicates across content-lifecycle pages.
 *
 * All keys use UPPERCASE to match the backend ENUM values.
 */

export interface PlatformConfig {
  /** Full display name (e.g. "YouTube") */
  label: string;
  /** Short abbreviation for compact UI (e.g. "YT") */
  short: string;
  /** Ant Design Tag color */
  color: string;
}

export const PLATFORM_CONFIG: Record<string, PlatformConfig> = {
  YOUTUBE: { label: 'YouTube', short: 'YT', color: 'red' },
  INSTAGRAM: { label: 'Instagram', short: 'IG', color: 'purple' },
  FACEBOOK: { label: 'Facebook', short: 'FB', color: 'blue' },
  X: { label: 'X (Twitter)', short: 'X', color: 'default' },
  NAVER_BLOG: { label: '네이버 블로그', short: 'Blog', color: 'green' },
};

/** Get platform config with a safe fallback. */
export function getPlatformConfig(platform: string): PlatformConfig {
  return PLATFORM_CONFIG[platform] ?? { label: platform, short: platform, color: 'default' };
}
