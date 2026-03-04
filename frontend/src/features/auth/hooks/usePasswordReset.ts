import { useMutation } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { PasswordResetBody, PasswordResetRequestBody } from '../types';

export function usePasswordResetRequest() {
  return useMutation({
    mutationFn: async (data: PasswordResetRequestBody) => {
      await apiClient.post('/auth/password/reset-request', data);
    },
  });
}

export function usePasswordReset() {
  return useMutation({
    mutationFn: async (data: PasswordResetBody) => {
      await apiClient.post('/auth/password/reset', data);
    },
  });
}
