import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import type {
  NotificationRecord,
  NotificationSettingRecord,
  NotificationSettingUpdateData,
  UnreadCountData,
} from '../types';

// ── Notification queries ────────────────────────────────

export function useNotifications(params: {
  page?: number;
  limit?: number;
  type?: string;
}, enabled = true) {
  return useQuery({
    queryKey: ['notifications', params],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<NotificationRecord>>('/notifications', {
        params,
      });
      return res.data;
    },
    enabled,
  });
}

export function useUnreadCount(enabled = true) {
  return useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<UnreadCountData>>('/notifications/unread-count');
      return res.data.data;
    },
    refetchInterval: enabled ? 30_000 : false,
    enabled,
  });
}

// ── Notification mutations ──────────────────────────────

export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string) => {
      const res = await apiClient.patch<ApiResponse<NotificationRecord>>(
        `/notifications/${notificationId}/read`,
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post<ApiResponse<{ affected: number }>>(
        '/notifications/mark-all-read',
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

// ── Notification settings ───────────────────────────────

export function useNotificationSettings() {
  return useQuery({
    queryKey: ['notification-settings'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<NotificationSettingRecord>>(
        '/notification-settings',
      );
      return res.data.data;
    },
  });
}

export function useUpdateNotificationSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: NotificationSettingUpdateData) => {
      const res = await apiClient.put<ApiResponse<NotificationSettingRecord>>(
        '/notification-settings',
        data,
      );
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-settings'] });
    },
  });
}

export function useSendTelegramTest() {
  return useMutation({
    mutationFn: async (chatId: string) => {
      const res = await apiClient.post<ApiResponse<{ sent: boolean; message: string }>>(
        '/notification-settings/telegram/test',
        { chat_id: chatId },
      );
      return res.data.data;
    },
  });
}
