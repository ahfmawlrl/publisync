/** 사용자 상태 + 기관 상태 공유 상수 */

export interface StatusConfig {
  color: string;
  text: string;
}

// ── 사용자 상태 ──────────────────────────────────

export const USER_STATUS_CONFIG: Record<string, StatusConfig> = {
  ACTIVE: { color: 'green', text: '활성' },
  INACTIVE: { color: 'default', text: '비활성' },
  LOCKED: { color: 'red', text: '잠금' },
  WITHDRAWN: { color: 'gray', text: '탈퇴' },
};

export function getUserStatusConfig(status: string): StatusConfig {
  return USER_STATUS_CONFIG[status] ?? { color: 'default', text: status };
}

export const USER_STATUS_FILTER_OPTIONS = [
  { value: '', label: '전체 상태' },
  { value: 'ACTIVE', label: '활성' },
  { value: 'INACTIVE', label: '비활성' },
  { value: 'LOCKED', label: '잠금' },
  { value: 'WITHDRAWN', label: '탈퇴' },
];

/** 사용자 수정 모달에서 사용하는 상태 옵션 */
export const USER_STATUS_OPTIONS = [
  { value: 'ACTIVE', label: '활성' },
  { value: 'INACTIVE', label: '비활성' },
  { value: 'LOCKED', label: '잠금' },
];

// ── 기관 상태 ──────────────────────────────────

export const ORG_STATUS_CONFIG: Record<string, StatusConfig> = {
  ACTIVE: { color: 'green', text: '활성' },
  INACTIVE: { color: 'default', text: '비활성' },
  SUSPENDED: { color: 'red', text: '정지' },
};

export function getOrgStatusConfig(status: string): StatusConfig {
  return ORG_STATUS_CONFIG[status] ?? { color: 'default', text: status };
}

// ── 기관 플랜 ──────────────────────────────────

export const PLAN_OPTIONS = [
  { value: 'FREE', label: '무료' },
  { value: 'BASIC', label: '베이직' },
  { value: 'PRO', label: '프로' },
  { value: 'ENTERPRISE', label: '엔터프라이즈' },
];
