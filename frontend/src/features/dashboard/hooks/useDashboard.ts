import { useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';

export interface DashboardSummary {
  total_contents: number;
  published_contents: number;
  scheduled_contents: number;
  pending_approvals: number;
  active_channels: number;
  total_views: number;
  total_likes: number;
}

export interface RecentContentItem {
  id: string;
  title: string;
  status: string;
  platforms: string[];
  created_at: string;
  author_id: string;
}

export interface TodayScheduleItem {
  id: string;
  title: string;
  scheduled_at: string;
  platforms: string[];
  status: string;
}

export interface ApprovalStatusItem {
  status: string;
  count: number;
}

export interface SentimentSummaryItem {
  sentiment: string;
  count: number;
  percentage: number;
}

export interface PlatformTrendItem {
  platform: string;
  published: number;
  views: number;
  likes: number;
  shares: number;
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<DashboardSummary>>('/dashboard/summary');
      return res.data.data;
    },
    refetchInterval: 300_000, // 5 min
  });
}

export function useRecentContents() {
  return useQuery({
    queryKey: ['dashboard', 'recent-contents'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<RecentContentItem[]>>('/dashboard/recent-contents', {
        params: { limit: 10 },
      });
      return res.data.data;
    },
    refetchInterval: 300_000,
  });
}

export function useTodaySchedule() {
  return useQuery({
    queryKey: ['dashboard', 'today-schedule'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<TodayScheduleItem[]>>('/dashboard/today-schedule');
      return res.data.data;
    },
    refetchInterval: 300_000,
  });
}

export function useApprovalStatus() {
  return useQuery({
    queryKey: ['dashboard', 'approval-status'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<ApprovalStatusItem[]>>('/dashboard/approval-status');
      return res.data.data;
    },
    refetchInterval: 300_000,
  });
}

export function useSentimentSummary() {
  return useQuery({
    queryKey: ['dashboard', 'sentiment-summary'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<SentimentSummaryItem[]>>('/dashboard/sentiment-summary');
      return res.data.data;
    },
    refetchInterval: 300_000,
  });
}

export function usePlatformTrends() {
  return useQuery({
    queryKey: ['dashboard', 'platform-trends'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<PlatformTrendItem[]>>('/dashboard/platform-trends');
      return res.data.data;
    },
    refetchInterval: 300_000,
  });
}
