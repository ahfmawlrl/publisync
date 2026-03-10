import axios from 'axios';

import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useWorkspaceStore } from '@/shared/stores/useWorkspaceStore';

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptors ─────────────────────────────────
apiClient.interceptors.request.use((config) => {
  // JWT injection
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Workspace injection
  const orgId = useWorkspaceStore.getState().currentOrgId;
  if (orgId) {
    config.headers['X-Workspace-Id'] = orgId;
  }
  return config;
});

// ── Response interceptors ────────────────────────────────
let refreshPromise: Promise<{ accessToken: string; refreshToken: string }> | null = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // 401 → attempt token refresh (once)
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const { refreshToken, setAccessToken, setRefreshToken, logout } = useAuthStore.getState();

      if (!refreshToken) {
        logout();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        // Share single refresh promise to prevent race condition
        if (!refreshPromise) {
          refreshPromise = axios
            .post('/api/v1/auth/refresh', { refresh_token: refreshToken })
            .then((res) => ({
              accessToken: res.data.data.access_token as string,
              refreshToken: res.data.data.refresh_token as string,
            }))
            .finally(() => {
              refreshPromise = null;
            });
        }
        const tokens = await refreshPromise;
        setAccessToken(tokens.accessToken);
        setRefreshToken(tokens.refreshToken);
        original.headers.Authorization = `Bearer ${tokens.accessToken}`;
        return apiClient(original);
      } catch {
        logout();
        window.location.href = '/login';
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
