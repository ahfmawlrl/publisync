/** 역할(Role) 공유 상수 — 단일 소스 */

export interface RoleConfig {
  label: string;
  /** Short abbreviation (SA, AM, AO, CD) */
  short: string;
  color: string;
}

export const ROLE_CONFIG: Record<string, RoleConfig> = {
  SYSTEM_ADMIN: { label: '시스템 관리자', short: 'SA', color: 'red' },
  AGENCY_MANAGER: { label: '수탁업체 관리자', short: 'AM', color: 'blue' },
  AGENCY_OPERATOR: { label: '수탁업체 실무자', short: 'AO', color: 'green' },
  CLIENT_DIRECTOR: { label: '위탁기관 담당자', short: 'CD', color: 'orange' },
};

/** 역할 설정 조회 (fallback: 기본값) */
export function getRoleConfig(role: string): RoleConfig {
  return ROLE_CONFIG[role] ?? { label: role, short: role, color: 'default' };
}

/** 역할 라벨만 조회 */
export function getRoleLabel(role: string): string {
  return ROLE_CONFIG[role]?.label ?? role;
}

/** 사용자 추가 시 선택 가능한 역할 (SA 제외) */
export const ROLE_OPTIONS = [
  { value: 'AGENCY_MANAGER', label: '수탁업체 관리자' },
  { value: 'AGENCY_OPERATOR', label: '수탁업체 실무자' },
  { value: 'CLIENT_DIRECTOR', label: '위탁기관 담당자' },
];

/** 역할 필터 옵션 (전체 포함) */
export const ROLE_FILTER_OPTIONS = [
  { value: '', label: '전체 역할' },
  { value: 'SYSTEM_ADMIN', label: '시스템 관리자' },
  { value: 'AGENCY_MANAGER', label: '수탁업체 관리자' },
  { value: 'AGENCY_OPERATOR', label: '수탁업체 실무자' },
  { value: 'CLIENT_DIRECTOR', label: '위탁기관 담당자' },
];
