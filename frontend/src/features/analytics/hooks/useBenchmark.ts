import { useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import type { BenchmarkData, OrgComparisonData } from '../types';

export function useBenchmark(period: string = '30d') {
  return useQuery({
    queryKey: ['benchmark', period],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<BenchmarkData>>(
        `/analytics/benchmark?period=${period}`,
      );
      return res.data.data;
    },
  });
}

export function useOrgComparison(period: string = '30d') {
  return useQuery({
    queryKey: ['benchmark-orgs', period],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<OrgComparisonData>>(
        `/analytics/benchmark/organizations?period=${period}`,
      );
      return res.data.data;
    },
  });
}
