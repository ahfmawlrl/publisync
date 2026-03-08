import type { CommentRecord } from './types';

/** Relative time formatter for comments (e.g. "5분 전", "3시간 전"). */
export function formatCommentTime(comment: CommentRecord): string {
  const dt = comment.platform_created_at || comment.created_at;
  const diff = Date.now() - new Date(dt).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}분 전`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}시간 전`;
  return new Date(dt).toLocaleDateString('ko-KR');
}
