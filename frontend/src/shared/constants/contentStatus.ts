/**
 * Unified content status constants — single source of truth.
 *
 * Replaces per-page STATUS_CONFIG / CONTENT_STATUS duplicates in:
 *   ContentsListPage, ContentDetailPage, DashboardPage, ApprovalsListPage
 */

/** Status config for rendering Tag components. */
export interface StatusConfig {
  color: string;
  text: string;
}

/**
 * Canonical content status mapping.
 *
 * Conventions:
 * - DRAFT: "작성 중" (진행형 — 명확한 상태 전달)
 * - APPROVED: cyan (green은 PUBLISHED와 혼동 방지)
 * - PENDING_REVIEW: "검토 대기" (통일)
 * - REJECTED: "반려됨" ('됨' 접미사 통일)
 */
export const CONTENT_STATUS_CONFIG: Record<string, StatusConfig> = {
  DRAFT: { color: 'default', text: '작성 중' },
  PENDING_REVIEW: { color: 'orange', text: '검토 대기' },
  IN_REVIEW: { color: 'processing', text: '검토 중' },
  APPROVED: { color: 'cyan', text: '승인됨' },
  REJECTED: { color: 'red', text: '반려됨' },
  SCHEDULED: { color: 'blue', text: '예약됨' },
  PUBLISHING: { color: 'processing', text: '게시 중' },
  PUBLISHED: { color: 'green', text: '게시 완료' },
  PARTIALLY_PUBLISHED: { color: 'warning', text: '부분 게시' },
  PUBLISH_FAILED: { color: 'error', text: '게시 실패' },
  CANCELLED: { color: 'default', text: '취소됨' },
  ARCHIVED: { color: 'default', text: '보관됨' },
};

/**
 * Approval-specific status subset (used by ApprovalsListPage).
 * Reuses the same colors/labels from CONTENT_STATUS_CONFIG.
 */
export const APPROVAL_STATUS_CONFIG: Record<string, StatusConfig> = {
  PENDING_REVIEW: CONTENT_STATUS_CONFIG.PENDING_REVIEW,
  IN_REVIEW: CONTENT_STATUS_CONFIG.IN_REVIEW,
  APPROVED: CONTENT_STATUS_CONFIG.APPROVED,
  REJECTED: CONTENT_STATUS_CONFIG.REJECTED,
};

/** Helper to get status config with a safe fallback. */
export function getStatusConfig(status: string): StatusConfig {
  return CONTENT_STATUS_CONFIG[status] ?? { color: 'default', text: status };
}
