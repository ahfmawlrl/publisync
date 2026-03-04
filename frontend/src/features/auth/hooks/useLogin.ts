import { useMutation } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import type { LoginRequest, LoginResponse } from '../types';

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);

  return useMutation({
    mutationFn: async (data: LoginRequest) => {
      const res = await apiClient.post<ApiResponse<LoginResponse>>('/auth/login', data);
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
