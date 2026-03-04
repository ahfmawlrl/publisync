import { describe, expect, it, beforeEach } from 'vitest';
import { useAuthStore } from './useAuthStore';

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.getState().logout();
  });

  it('should start with no user', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
  });

  it('should set auth state on setAuth', () => {
    useAuthStore.getState().setAuth(
      { accessToken: 'access-123', refreshToken: 'refresh-456' },
      { id: '1', email: 'test@test.com', name: 'Test', role: 'AGENCY_MANAGER', status: 'ACTIVE' },
    );
    const state = useAuthStore.getState();
    expect(state.accessToken).toBe('access-123');
    expect(state.refreshToken).toBe('refresh-456');
    expect(state.user?.email).toBe('test@test.com');
  });

  it('should update access token on setAccessToken', () => {
    useAuthStore.getState().setAccessToken('new-token');
    expect(useAuthStore.getState().accessToken).toBe('new-token');
  });

  it('should clear state on logout', () => {
    useAuthStore.getState().setAuth(
      { accessToken: 'a', refreshToken: 'b' },
      { id: '1', email: 'x@x.com', name: 'X', role: 'SYSTEM_ADMIN', status: 'ACTIVE' },
    );
    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.user).toBeNull();
  });
});
