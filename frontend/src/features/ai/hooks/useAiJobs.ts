/**
 * TanStack Query hooks for async AI jobs — S18 (F03/F15).
 *
 * Pattern: POST → 202 Accepted (jobId) → polling GET /ai/jobs/:jobId
 * Uses mutations for job creation, queries with refetchInterval for polling.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';

// ── Types ───────────────────────────────────────────────

interface AiJobCreateResponse {
  job_id: string;
  job_type: string;
  status: string;
  message: string;
}

interface AiJobStatus {
  job_id: string;
  job_type: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress: number;
  result: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

interface SubtitleRequest {
  media_asset_id: string;
  language?: string;
  include_timestamps?: boolean;
}

interface ShortformRequest {
  media_asset_id: string;
  target_duration?: number;
  count?: number;
  style?: string;
}

interface ThumbnailRequest {
  content_text: string;
  style?: string;
  count?: number;
  aspect_ratio?: string;
}

// ── Mutations ───────────────────────────────────────────

/**
 * Create an async subtitle generation job (F03).
 * POST /api/v1/ai/generate-subtitles → 202 Accepted
 */
export function useCreateSubtitles() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SubtitleRequest) => {
      const res = await apiClient.post<ApiResponse<AiJobCreateResponse>>(
        '/ai/generate-subtitles',
        data,
      );
      return res.data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ai-jobs'] }),
  });
}

/**
 * Create an async shortform extraction job (F15).
 * POST /api/v1/ai/extract-shortform → 202 Accepted
 */
export function useCreateShortform() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: ShortformRequest) => {
      const res = await apiClient.post<ApiResponse<AiJobCreateResponse>>(
        '/ai/extract-shortform',
        data,
      );
      return res.data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ai-jobs'] }),
  });
}

/**
 * Save edited subtitles to the server (F03).
 * PUT /api/v1/media/:id/subtitles
 */
export function useSaveSubtitles() {
  return useMutation({
    mutationFn: async (data: { mediaAssetId: string; subtitles: { start: number; end: number; text: string }[] }) => {
      const res = await apiClient.put<ApiResponse<{ saved: boolean }>>(
        `/media/${data.mediaAssetId}/subtitles`,
        { subtitles: data.subtitles },
      );
      return res.data.data;
    },
  });
}

/**
 * Create an async thumbnail generation job (F16).
 * POST /api/v1/ai/generate-thumbnail → 202 Accepted
 */
export function useCreateThumbnail() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: ThumbnailRequest) => {
      const res = await apiClient.post<ApiResponse<AiJobCreateResponse>>(
        '/ai/generate-thumbnail',
        data,
      );
      return res.data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ai-jobs'] }),
  });
}

/**
 * Confirm selected shortform clips (F15).
 * POST /api/v1/ai/shortform/confirm
 */
export function useConfirmShortform() {
  return useMutation({
    mutationFn: async (data: { media_asset_id: string; clips: Record<string, unknown>[] }) => {
      const res = await apiClient.post<ApiResponse<{ confirmed: boolean; clip_count: number }>>(
        '/ai/shortform/confirm',
        data,
      );
      return res.data.data;
    },
  });
}

// ── Queries ─────────────────────────────────────────────

/**
 * Poll async job status every 3 seconds until COMPLETED or FAILED.
 * GET /api/v1/ai/jobs/:jobId
 */
export function useJobStatus(
  jobId: string | null,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ['ai-jobs', jobId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<AiJobStatus>>(
        `/ai/jobs/${jobId}`,
      );
      return res.data.data;
    },
    enabled: !!jobId && options?.enabled !== false,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      if (data.status === 'COMPLETED' || data.status === 'FAILED') return false;
      return 3000; // Poll every 3 seconds while processing
    },
  });
}
