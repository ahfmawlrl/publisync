import { useQuery } from '@tanstack/react-query';
import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import type { SentimentTrendData } from '../types';

export function useSentimentTrend(period: string = '30d') {
  return useQuery({
    queryKey: ['sentiment-trend', period],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<SentimentTrendData>>(
        `/analytics/sentiment-trend?period=${period}`,
      );
      return res.data.data;
    },
  });
}
