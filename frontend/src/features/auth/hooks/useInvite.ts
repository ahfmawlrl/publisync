import { useMutation, useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import type { InviteAcceptRequest, InviteVerifyResponse, LoginResponse } from '../types';

export function useInviteVerify(token: string | null) {
  return useQuery({
    queryKey: ['invite', 'verify', token],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<InviteVerifyResponse>>('/auth/invite/verify', {
        params: { token },
      });
      return res.data.data;
    },
    enabled: !!token,
  });
}

export function useInviteAccept() {
  const setAuth = useAuthStore((s) => s.setAuth);

  return useMutation({
    mutationFn: async (data: InviteAcceptRequest) => {
      const res = await apiClient.post<ApiResponse<LoginResponse>>('/auth/invite/accept', data);
      return res.data.data;
    },
    onSuccess: (data) => {
      setAuth(
        {
          accessToken: data.tokens.access_token,
          refreshToken: data.tokens.refresh_token,
        },
        {
          id: data.user.id,
          email: data.user.email,
          name: data.user.name,
          role: data.user.role,
          status: data.user.status,
        },
      );
    },
  });
}
