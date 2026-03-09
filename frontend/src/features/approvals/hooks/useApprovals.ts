import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import type { ApprovalRequestRecord, WorkflowRecord } from '../types';

export function useApprovals(params: { page?: number; status?: string; requested_by?: string }) {
  return useQuery({
    queryKey: ['approvals', params],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ApprovalRequestRecord>>('/approvals', { params });
      return res.data;
    },
  });
}

export function useApproval(approvalId: string | null) {
  return useQuery({
    queryKey: ['approvals', approvalId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<ApprovalRequestRecord>>(`/approvals/${approvalId}`);
      return res.data.data;
    },
    enabled: !!approvalId,
  });
}

export function useApproveRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, comment }: { id: string; comment?: string }) => {
      const res = await apiClient.post<ApiResponse<ApprovalRequestRecord>>(
        `/approvals/${id}/approve`,
        { comment },
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useRejectRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, comment }: { id: string; comment?: string }) => {
      const res = await apiClient.post<ApiResponse<ApprovalRequestRecord>>(
        `/approvals/${id}/reject`,
        { comment },
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useWorkflows() {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<WorkflowRecord[]>>('/approvals/workflows');
      return res.data.data;
    },
  });
}

export function useUpdateWorkflow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name?: string; steps?: Record<string, unknown>[]; is_active?: boolean }) => {
      const res = await apiClient.put<ApiResponse<WorkflowRecord>>('/approvals/workflows', data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });
}
