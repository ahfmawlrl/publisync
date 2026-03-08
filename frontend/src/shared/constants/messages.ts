/**
 * Unified toast / feedback message constants — single source of truth.
 *
 * Convention: `'~이(가) 완료되었습니다'` / `'~에 실패했습니다'` pattern.
 * Replaces inconsistent inline strings across content-lifecycle pages.
 */

export const CONTENT_MESSAGES = {
  // Create / Edit
  CREATE_SUCCESS: '콘텐츠가 작성되었습니다',
  CREATE_ERROR: '콘텐츠 작성에 실패했습니다',
  UPDATE_SUCCESS: '콘텐츠가 수정되었습니다',
  UPDATE_ERROR: '콘텐츠 수정에 실패했습니다',

  // Draft
  SAVE_DRAFT_SUCCESS: '임시 저장이 완료되었습니다',
  SAVE_DRAFT_ERROR: '임시 저장에 실패했습니다',

  // Review
  REQUEST_REVIEW_SUCCESS: '검토 요청이 완료되었습니다',
  REQUEST_REVIEW_ERROR: '검토 요청에 실패했습니다',

  // Delete
  DELETE_SUCCESS: '콘텐츠가 삭제되었습니다',
  DELETE_ERROR: '콘텐츠 삭제에 실패했습니다',
  DELETE_CONFIRM: '콘텐츠를 삭제하시겠습니까?',

  // Publish
  CANCEL_PUBLISH_SUCCESS: '게시가 취소되었습니다',
  CANCEL_PUBLISH_ERROR: '게시 취소에 실패했습니다',
  RETRY_PUBLISH_SUCCESS: '재게시가 요청되었습니다',
  RETRY_PUBLISH_ERROR: '재게시 요청에 실패했습니다',

  // Bulk
  BULK_SUCCESS: '일괄 처리가 완료되었습니다',
  BULK_ERROR: '일괄 처리에 실패했습니다',
} as const;

export const APPROVAL_MESSAGES = {
  APPROVE_SUCCESS: '승인이 완료되었습니다',
  APPROVE_ERROR: '승인 처리에 실패했습니다',
  REJECT_SUCCESS: '반려가 완료되었습니다',
  REJECT_ERROR: '반려 처리에 실패했습니다',
  REJECT_CONFIRM: '반려 사유를 입력하세요',
} as const;

export const NOTIFICATION_MESSAGES = {
  MARK_READ_SUCCESS: '읽음 처리되었습니다',
  MARK_ALL_READ_SUCCESS: (count: number) => `${count}개 알림을 읽음 처리했습니다`,
  MARK_ALL_READ_ERROR: '일괄 읽음 처리에 실패했습니다',
} as const;
