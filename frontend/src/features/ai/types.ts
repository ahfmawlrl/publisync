/** AI feature types — S11 (F02). */

/** Request body for AI text generation endpoints. */
export interface AiGenerateRequest {
  content_text: string;
  platform?: string;
  language?: string;
  count?: number;
}

/** Single AI-generated suggestion with confidence score. */
export interface AiSuggestion {
  content: string;
  score: number;
}

/** Token usage information from an AI request. */
export interface AiUsageInfo {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost: number;
}

/** Standard Human-in-the-Loop AI response with suggestions. */
export interface AiGenerateResponse {
  isAiGenerated: boolean;
  confidence: number;
  fallbackAvailable: boolean;
  model: string;
  suggestions: AiSuggestion[];
  usage: AiUsageInfo;
  processing_time_ms: number;
  error?: string | null;
}

/** Per-task-type usage breakdown. */
export interface AiTaskTypeUsage {
  task_type: string;
  request_count: number;
  total_tokens: number;
  estimated_cost: number;
}

/** Aggregated AI usage statistics for an organization. */
export interface AiUsageResponse {
  organization_id: string;
  total_requests: number;
  total_tokens: number;
  estimated_cost: number;
  by_task_type: AiTaskTypeUsage[];
}

// ── S17 — AI Synchronous Features (F05/F17/F21) ──────────

/** Request body for AI reply generation (F05). */
export interface AiReplyRequest {
  comment_text: string;
  content_context?: string | null;
  tone?: string;
  count?: number;
}

/** Request body for tone transformation (F17). */
export interface AiToneTransformRequest {
  content_text: string;
  target_platform: string;
  target_tone?: string;
  count?: number;
}

/** Request body for content review/audit (F21). */
export interface AiContentReviewRequest {
  content_text: string;
  check_spelling?: boolean;
  check_sensitivity?: boolean;
  check_bias?: boolean;
}

/** Single review issue found by AI. */
export interface AiContentReviewIssue {
  issue: string;
  severity: string;
  location?: string | null;
  suggestion: string;
  score: number;
}

/** Content review response with issues list. */
export interface AiContentReviewResponse {
  isAiGenerated: boolean;
  confidence: number;
  fallbackAvailable: boolean;
  model: string;
  issues: AiContentReviewIssue[];
  summary: string;
  usage: AiUsageInfo;
  processing_time_ms: number;
  error?: string | null;
}

/** Request body for effects/emoji suggestion (F03). */
export interface AiSuggestEffectsRequest {
  content_text: string;
  content_type?: string;
  count?: number;
}

/** Request body for template improvement (F05). */
export interface AiImproveTemplateRequest {
  template_text: string;
  purpose?: string;
  count?: number;
}

// ── Phase 4 — Translation (F22) + Thumbnail (F16) ──────────

/** Request body for AI translation (F22). */
export interface AiTranslateRequest {
  content_text: string;
  target_language: string; // en, zh, ja, vi
  source_language?: string; // default: ko
  preserve_formatting?: boolean;
}

/** AI translation response (F22). */
export interface AiTranslateResponse {
  isAiGenerated: boolean;
  confidence: number;
  fallbackAvailable: boolean;
  model: string;
  translated_text: string;
  target_language: string;
  source_language: string;
  notes: string;
  usage: AiUsageInfo;
  processing_time_ms: number;
  error?: string | null;
}

/** Request body for AI thumbnail generation (F16, async). */
export interface AiThumbnailRequest {
  content_text: string;
  style?: string; // modern, classic, minimalist, bold
  count?: number; // 1-5
  aspect_ratio?: string; // 16:9, 1:1, 4:3, 9:16
}
