import { useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import type { AnalyticsFilters, EngagementHeatmapItem, PerformanceData, TopContentItem, TrendItem } from '../types';

export function usePerformance(params: AnalyticsFilters = {}) {
  return useQuery({
    queryKey: ['analytics', 'performance', params],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<PerformanceData[]>>('/analytics/performance', {
        params,
      });
      return res.data.data;
    },
    refetchInterval: 300_000, // 5 min
  });
}

export function useEngagementHeatmap(period: string = '30d') {
  return useQuery({
    queryKey: ['analytics', 'engagement-heatmap', period],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<EngagementHeatmapItem[]>>(
        '/analytics/engagement-heatmap',
        { params: { period } },
      );
      return res.data.data;
    },
    refetchInterval: 300_000,
  });
}

export function useTrend(period: string = '30d', granularity: string = 'daily') {
  return useQuery({
    queryKey: ['analytics', 'trend', period, granularity],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<TrendItem[]>>('/analytics/trend', {
        params: { period, granularity },
      });
      return res.data.data;
    },
    refetchInterval: 300_000,
  });
}

export function useTopContents(period: string = '30d', limit: number = 5) {
  return useQuery({
    queryKey: ['analytics', 'top-contents', period, limit],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<TopContentItem[]>>('/analytics/top-contents', {
        params: { period, limit },
      });
      return res.data.data;
    },
    refetchInterval: 300_000,
  });
}

export async function exportPerformance(params: { format?: string; period?: string } = {}) {
  const res = await apiClient.get('/analytics/performance/export', {
    params: { format: params.format ?? 'csv', period: params.period ?? '30d' },
    responseType: 'blob',
  });
  // Trigger browser download
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `performance_${params.period ?? '30d'}.csv`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
