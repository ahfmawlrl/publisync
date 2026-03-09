/**
 * AI usage statistics and job list hooks — S11 (F02).
 */

import { useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import type { AiUsageResponse } from '../types';

/** Single AI job in list */
export interface AiJobListItem {
  job_id: string;
  job_type: string;
  status: string;
  progress: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

/** GET /ai/usage — AI usage statistics for current org (AM only) */
export function useAiUsage() {
  return useQuery({
    queryKey: ['ai-usage'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<AiUsageResponse>>('/ai/usage');
      return res.data.data;
    },
    staleTime: 60_000,
  });
}

/** GET /ai/jobs — List AI jobs with pagination */
export function useAiJobs(params: {
  page?: number;
  limit?: number;
  jobType?: string;
  status?: string;
}) {
  return useQuery({
    queryKey: ['ai-jobs-list', params],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<AiJobListItem>>('/ai/jobs', {
        params: {
          page: params.page ?? 1,
          limit: params.limit ?? 20,
          ...(params.jobType ? { job_type: params.jobType } : {}),
          ...(params.status ? { status: params.status } : {}),
        },
      });
      return res.data;
    },
    staleTime: 30_000,
  });
}
