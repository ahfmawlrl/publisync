import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import type { GenerateReportRequest, Report, ReportListItem } from '../types';

interface ReportListResponse {
  data: ReportListItem[];
  meta: { total: number; page: number; limit: number };
}

export function useReportsList(filters?: { period?: string; status?: string; page?: number }) {
  return useQuery({
    queryKey: ['reports', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.period) params.set('period', filters.period);
      if (filters?.status) params.set('status', filters.status);
      if (filters?.page) params.set('page', String(filters.page));
      const res = await apiClient.get<ApiResponse<ReportListItem[]> & { meta: ReportListResponse['meta'] }>(`/reports?${params.toString()}`);
      return { data: res.data.data, meta: (res.data as any).meta };
    },
  });
}

export function useReport(id: string | undefined) {
  return useQuery({
    queryKey: ['reports', id],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<Report>>(`/reports/${id}`);
      return res.data.data;
    },
    enabled: !!id,
  });
}

export function useGenerateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: GenerateReportRequest) => {
      const res = await apiClient.post<ApiResponse<{ report_id: string; job_id: string }>>('/reports/generate', body);
      return res.data.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  });
}

export function useUpdateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...body }: { id: string; title?: string; content?: Record<string, unknown> }) => {
      const res = await apiClient.put<ApiResponse<{ id: string }>>(`/reports/${id}`, body);
      return res.data.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  });
}

export function useFinalizeReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<ApiResponse<{ id: string }>>(`/reports/${id}/finalize`);
      return res.data.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  });
}
