import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse, PaginationMeta } from '@/shared/api/types';
import type {
  MediaAsset,
  MediaAssetListItem,
  MediaFolder,
  MediaFolderCreateData,
  MediaListParams,
  MediaUpdateData,
  MediaUploadData,
  PresignedUploadData,
  PresignedUploadResult,
  StorageStats,
} from '../types';

/** list_media 응답의 확장 meta (storage 포함) */
interface MediaListMeta extends PaginationMeta {
  storage?: StorageStats;
}

export function useMediaList(params: MediaListParams) {
  return useQuery({
    queryKey: ['media', params],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<MediaAssetListItem, MediaListMeta>>('/media', { params });
      return res.data;
    },
  });
}

export function useMediaAsset(id: string | null) {
  return useQuery({
    queryKey: ['media', id],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<MediaAsset>>(`/media/${id}`);
      return res.data.data;
    },
    enabled: !!id,
  });
}

export function useUploadMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: MediaUploadData) => {
      const res = await apiClient.post<ApiResponse<MediaAsset>>('/media/upload', data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['media'] });
    },
  });
}

export function useUpdateMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: MediaUpdateData }) => {
      const res = await apiClient.put<ApiResponse<MediaAsset>>(`/media/${id}`, data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['media'] });
    },
  });
}

export function useDeleteMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/media/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['media'] });
    },
  });
}

export function useMediaFolders() {
  return useQuery({
    queryKey: ['media', 'folders'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<MediaFolder[]>>('/media/folders');
      return res.data.data;
    },
  });
}

export function useCreateFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: MediaFolderCreateData) => {
      const res = await apiClient.post<ApiResponse<MediaFolder>>('/media/folders', data);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['media', 'folders'] });
    },
  });
}

export function usePresignedUpload() {
  return useMutation({
    mutationFn: async (data: PresignedUploadData) => {
      const res = await apiClient.post<ApiResponse<PresignedUploadResult>>(
        '/media/presigned-upload',
        data,
      );
      return res.data.data;
    },
  });
}
