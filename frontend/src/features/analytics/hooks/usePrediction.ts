import { useMutation, useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import type { PredictionData } from '../types';

export function usePrediction(contentId?: string) {
  return useQuery({
    queryKey: ['prediction', contentId],
    queryFn: async () => {
      const params = contentId ? `?content_id=${contentId}` : '';
      const res = await apiClient.get<ApiResponse<PredictionData>>(
        `/analytics/prediction${params}`,
      );
      return res.data.data;
    },
  });
}

export function useOptimalTime() {
  return useMutation({
    mutationFn: async (body: { content_text: string; platforms: string[] }) => {
      const res = await apiClient.post<
        ApiResponse<{
          isAiGenerated: boolean;
          optimal_times: Array<{
            day_of_week: string;
            time_range: string;
            reason: string;
            confidence: number;
          }>;
          confidence: number;
          model: string;
        }>
      >('/ai/optimal-time', body);
      return res.data.data;
    },
  });
}
