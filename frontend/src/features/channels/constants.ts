/** Channel-specific constants shared across channel pages. */

export const CHANNEL_STATUS_CONFIG: Record<string, { color: string; text: string }> = {
  ACTIVE: { color: 'green', text: '연동됨' },
  EXPIRING: { color: 'orange', text: '만료 임박' },
  EXPIRED: { color: 'red', text: '만료됨' },
  DISCONNECTED: { color: 'default', text: '미연동' },
};

export const CHANNEL_EVENT_LABELS: Record<string, string> = {
  CONNECTED: '채널 연동',
  DISCONNECTED: '연동 해제',
  TOKEN_REFRESHED: '토큰 갱신',
  TOKEN_EXPIRED: '토큰 만료',
  STATUS_CHANGED: '상태 변경',
};

export const CHANNEL_EVENT_COLORS: Record<string, string> = {
  CONNECTED: 'green',
  DISCONNECTED: 'default',
  TOKEN_REFRESHED: 'blue',
  TOKEN_EXPIRED: 'red',
  STATUS_CHANGED: 'orange',
};
