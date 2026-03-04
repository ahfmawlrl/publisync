import { useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { PaginatedResponse } from '@/shared/api/types';
import type { AuditLogFilters, AuditLogRecord } from '../types';

export function useAuditLogs(params: AuditLogFilters) {
  return useQuery({
    queryKey: ['audit-logs', params],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<AuditLogRecord>>('/audit-logs', { params });
      return res.data;
    },
  });
}

export function useAuditLogDetail(logId: string | null) {
  return useQuery({
    queryKey: ['audit-logs', logId],
    queryFn: async () => {
      const res = await apiClient.get<{ success: boolean; data: AuditLogRecord }>(
        `/audit-logs/${logId}`,
      );
      return res.data.data;
    },
    enabled: !!logId,
  });
}

export async function exportAuditLogs(params: {
  format: string;
  start_date: string;
  end_date: string;
  actions?: string;
}) {
  const res = await apiClient.get('/audit-logs/export', {
    params,
    responseType: 'blob',
  });
  // Trigger browser download
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `audit_logs_${params.start_date}_${params.end_date}.csv`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
