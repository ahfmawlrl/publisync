import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import type { ApiStatusRecord, ChannelHistoryRecord, ChannelRecord, ConnectInitiateResponse } from '../types';

export function useChannels(page: number = 1) {
  return useQuery({
    queryKey: ['channels', { page }],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ChannelRecord>>('/channels', {
        params: { page, limit: 20 },
      });
      return res.data;
    },
  });
}

export function useChannelHistory(channelId: string | null, page: number = 1) {
  return useQuery({
    queryKey: ['channels', channelId, 'history', { page }],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ChannelHistoryRecord>>(
        `/channels/${channelId}/history`,
        { params: { page, limit: 50 } },
      );
      return res.data;
    },
    enabled: !!channelId,
  });
}

export function useApiStatus() {
  return useQuery({
    queryKey: ['channels', 'api-status'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<ApiStatusRecord[]>>('/channels/api-status');
      return res.data.data;
    },
    refetchInterval: 60_000,
  });
}

export function useConnectChannel() {
  const queryClient = useQueryClient();

  const initiate = useMutation({
    mutationFn: async (body: { platform: string; redirect_uri: string }) => {
      const res = await apiClient.post<ApiResponse<ConnectInitiateResponse>>(
        '/channels/connect/initiate',
        body,
      );
      return res.data.data;
    },
  });

  const callback = useMutation({
    mutationFn: async (body: { platform: string; code: string; state: string; redirect_uri: string }) => {
      const res = await apiClient.post<ApiResponse<ChannelRecord>>('/channels/connect/callback', body);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });

  return { initiate, callback };
}

export function useDisconnectChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (channelId: string) => {
      await apiClient.delete(`/channels/${channelId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}

export function useRefreshChannelToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (channelId: string) => {
      const res = await apiClient.post<ApiResponse<ChannelRecord>>(`/channels/${channelId}/refresh-token`);
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });
}
