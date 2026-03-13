import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import type {
  ContentCreateData,
  ContentRecord,
  ContentUpdateData,
  PublishResultRecord,
  VariantCreateData,
  VariantMediaAttachData,
  VariantMediaRecord,
  VariantRecord,
  VariantUpdateData,
} from '../types';

export function useContents(params: {
  page?: number;
  limit?: number;
  status?: string;
  platform?: string;
  search?: string;
  period?: string;
}) {
  return useQuery({
    queryKey: ['contents', params],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ContentRecord>>('/contents', { params });
      return res.data;
    },
  });
}

export function useContent(contentId: string | null) {
  return useQuery({
    queryKey: ['contents', contentId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<ContentRecord>>(`/contents/${contentId}`);
      return res.data.data;
    },
    enabled: !!contentId,
  });
}

export function useCreateContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: ContentCreateData) => {
      const res = await apiClient.post<ApiResponse<ContentRecord>>('/contents', data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useUpdateContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: ContentUpdateData }) => {
      const res = await apiClient.put<ApiResponse<ContentRecord>>(`/contents/${id}`, data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useDeleteContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/contents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useSaveDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: ContentUpdateData }) => {
      const res = await apiClient.post<ApiResponse<ContentRecord>>(`/contents/${id}/save-draft`, data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useRequestReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<ApiResponse<ContentRecord>>(`/contents/${id}/request-review`);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function usePublishHistory(contentId: string | null, page: number = 1) {
  return useQuery({
    queryKey: ['contents', contentId, 'publish-history', { page }],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<PublishResultRecord>>(
        `/contents/${contentId}/publish-history`,
        { params: { page, limit: 50 } },
      );
      return res.data;
    },
    enabled: !!contentId,
  });
}

export function usePublishContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<ApiResponse<ContentRecord>>(`/contents/${id}/publish`);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useRetryPublish() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<ApiResponse<ContentRecord>>(`/contents/${id}/retry-publish`);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useBulkAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { content_ids: string[]; action: string }) => {
      const res = await apiClient.post<ApiResponse<{ affected: number }>>('/contents/bulk-action', data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useCancelPublish() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post<ApiResponse<ContentRecord>>(`/contents/${id}/cancel-publish`);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

// ── v2.0: Variant hooks ─────────────────────────────

export function useVariants(contentId: string | null) {
  return useQuery({
    queryKey: ['contents', contentId, 'variants'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<VariantRecord[]>>(
        `/contents/${contentId}/variants`,
      );
      return res.data.data;
    },
    enabled: !!contentId,
  });
}

export function useCreateVariant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ contentId, data }: { contentId: string; data: VariantCreateData }) => {
      const res = await apiClient.post<ApiResponse<VariantRecord>>(
        `/contents/${contentId}/variants`,
        data,
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useUpdateVariant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      contentId,
      variantId,
      data,
    }: {
      contentId: string;
      variantId: string;
      data: VariantUpdateData;
    }) => {
      const res = await apiClient.put<ApiResponse<VariantRecord>>(
        `/contents/${contentId}/variants/${variantId}`,
        data,
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useDeleteVariant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ contentId, variantId }: { contentId: string; variantId: string }) => {
      await apiClient.delete(`/contents/${contentId}/variants/${variantId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useAttachVariantMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      contentId,
      variantId,
      data,
    }: {
      contentId: string;
      variantId: string;
      data: VariantMediaAttachData;
    }) => {
      const res = await apiClient.post<ApiResponse<VariantMediaRecord>>(
        `/contents/${contentId}/variants/${variantId}/media`,
        data,
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}

export function useDetachVariantMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      contentId,
      variantId,
      mediaId,
    }: {
      contentId: string;
      variantId: string;
      mediaId: string;
    }) => {
      await apiClient.delete(
        `/contents/${contentId}/variants/${variantId}/media/${mediaId}`,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}
