/**
 * TanStack Query mutation hooks for AI endpoints — S11 (F02).
 *
 * All hooks use mutations (not queries) because AI generation is an
 * explicit user action, not background data fetching.
 */

import { useMutation } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import type {
  AiContentReviewRequest,
  AiContentReviewResponse,
  AiGenerateRequest,
  AiGenerateResponse,
  AiImproveTemplateRequest,
  AiReplyRequest,
  AiSuggestEffectsRequest,
  AiToneTransformRequest,
  AiTranslateRequest,
  AiTranslateResponse,
} from '../types';

/**
 * Generate title suggestions for content.
 * POST /api/v1/ai/generate-title
 */
export function useGenerateTitle() {
  return useMutation({
    mutationFn: async (data: AiGenerateRequest) => {
      const res = await apiClient.post<ApiResponse<AiGenerateResponse>>(
        '/ai/generate-title',
        data,
      );
      return res.data.data;
    },
  });
}

/**
 * Generate description suggestions for content.
 * POST /api/v1/ai/generate-description
 */
export function useGenerateDescription() {
  return useMutation({
    mutationFn: async (data: AiGenerateRequest) => {
      const res = await apiClient.post<ApiResponse<AiGenerateResponse>>(
        '/ai/generate-description',
        data,
      );
      return res.data.data;
    },
  });
}

/**
 * Generate hashtag suggestions for content.
 * POST /api/v1/ai/generate-hashtags
 */
export function useGenerateHashtags() {
  return useMutation({
    mutationFn: async (data: AiGenerateRequest) => {
      const res = await apiClient.post<ApiResponse<AiGenerateResponse>>(
        '/ai/generate-hashtags',
        data,
      );
      return res.data.data;
    },
  });
}

// ── S17 — AI Synchronous Features (F05/F17/F21) ──────────

/**
 * Generate AI reply drafts for a comment (F05).
 * POST /api/v1/ai/generate-reply
 */
export function useGenerateReply() {
  return useMutation({
    mutationFn: async (data: AiReplyRequest) => {
      const res = await apiClient.post<ApiResponse<AiGenerateResponse>>(
        '/ai/generate-reply',
        data,
      );
      return res.data.data;
    },
  });
}

/**
 * Improve a reply template (F05).
 * POST /api/v1/ai/improve-template
 */
export function useImproveTemplate() {
  return useMutation({
    mutationFn: async (data: AiImproveTemplateRequest) => {
      const res = await apiClient.post<ApiResponse<AiGenerateResponse>>(
        '/ai/improve-template',
        data,
      );
      return res.data.data;
    },
  });
}

/**
 * Transform content tone for a target platform (F17).
 * POST /api/v1/ai/tone-transform
 */
export function useToneTransform() {
  return useMutation({
    mutationFn: async (data: AiToneTransformRequest) => {
      const res = await apiClient.post<ApiResponse<AiGenerateResponse>>(
        '/ai/tone-transform',
        data,
      );
      return res.data.data;
    },
  });
}

/**
 * Review content for issues — spelling, sensitivity, bias (F21).
 * POST /api/v1/ai/content-review
 */
export function useContentReview() {
  return useMutation({
    mutationFn: async (data: AiContentReviewRequest) => {
      const res = await apiClient.post<ApiResponse<AiContentReviewResponse>>(
        '/ai/content-review',
        data,
      );
      return res.data.data;
    },
  });
}

/**
 * Suggest emojis and sound effects for content (F03).
 * POST /api/v1/ai/suggest-effects
 */
export function useSuggestEffects() {
  return useMutation({
    mutationFn: async (data: AiSuggestEffectsRequest) => {
      const res = await apiClient.post<ApiResponse<AiGenerateResponse>>(
        '/ai/suggest-effects',
        data,
      );
      return res.data.data;
    },
  });
}

// ── Phase 4 — Translation (F22) ──────────────────────────

/**
 * Translate content to a target language (F22).
 * POST /api/v1/ai/translate (synchronous, < 10s)
 */
export function useTranslate() {
  return useMutation({
    mutationFn: async (data: AiTranslateRequest) => {
      const res = await apiClient.post<ApiResponse<AiTranslateResponse>>(
        '/ai/translate',
        data,
      );
      return res.data.data;
    },
  });
}
