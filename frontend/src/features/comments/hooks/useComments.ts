import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import type {
  CommentRecord,
  ReplyTemplateCreateData,
  ReplyTemplateRecord,
  ReplyTemplateUpdateData,
} from '../types';

// ── Comment queries ─────────────────────────────────────

export function useComments(params: {
  page?: number;
  limit?: number;
  status?: string;
  platform?: string;
  channel_id?: string;
  search?: string;
  sentiment?: string;
}) {
  return useQuery({
    queryKey: ['comments', params],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<CommentRecord>>('/comments', { params });
      return res.data;
    },
  });
}

export function useComment(commentId: string | null) {
  return useQuery({
    queryKey: ['comments', commentId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<CommentRecord>>(`/comments/${commentId}`);
      return res.data.data;
    },
    enabled: !!commentId,
  });
}

export function useDangerousComments(params: { page?: number; limit?: number; status?: string }) {
  return useQuery({
    queryKey: ['comments', 'dangerous', params],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<CommentRecord>>('/comments/dangerous', {
        params,
      });
      return res.data;
    },
  });
}

// ── Comment mutations ───────────────────────────────────

export function useReplyComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, text }: { id: string; text: string }) => {
      const res = await apiClient.post<ApiResponse<CommentRecord>>(`/comments/${id}/reply`, {
        text,
      });
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments'] });
    },
  });
}

export function useHideComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason?: string }) => {
      const res = await apiClient.post<ApiResponse<CommentRecord>>(`/comments/${id}/hide`, {
        reason,
      });
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments'] });
    },
  });
}

export function useDeleteRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason?: string }) => {
      const res = await apiClient.post<ApiResponse<CommentRecord>>(
        `/comments/${id}/delete-request`,
        { reason },
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments'] });
    },
  });
}

export function useIgnoreDangerous() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<ApiResponse<CommentRecord>>(`/comments/${id}/ignore`);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments'] });
    },
  });
}

export function useApproveDelete() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<ApiResponse<CommentRecord>>(
        `/comments/${id}/delete-approve`,
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments'] });
    },
  });
}

// ── Reply Template queries ──────────────────────────────

export function useReplyTemplates(category?: string) {
  return useQuery({
    queryKey: ['reply-templates', { category }],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<ReplyTemplateRecord[]>>('/reply-templates', {
        params: category ? { category } : undefined,
      });
      return res.data.data;
    },
  });
}

export function useCreateReplyTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: ReplyTemplateCreateData) => {
      const res = await apiClient.post<ApiResponse<ReplyTemplateRecord>>('/reply-templates', data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reply-templates'] });
    },
  });
}

export function useUpdateReplyTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: ReplyTemplateUpdateData }) => {
      const res = await apiClient.put<ApiResponse<ReplyTemplateRecord>>(
        `/reply-templates/${id}`,
        data,
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reply-templates'] });
    },
  });
}

export function useDeleteReplyTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/reply-templates/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reply-templates'] });
    },
  });
}
