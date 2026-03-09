import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import RouteGuard from './RouteGuard';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useWorkspaceStore } from '@/shared/stores/useWorkspaceStore';

// Mock useWorkspace to avoid real API calls
vi.mock('@/shared/hooks/useWorkspace', () => ({
  useWorkspace: () => ({
    workspaces: useWorkspaceStore.getState().orgList,
    currentOrgId: useWorkspaceStore.getState().currentOrgId,
    switchWorkspace: vi.fn(),
    isLoading: false,
  }),
}));

function renderWithProviders(
  ui: React.ReactElement,
  { initialEntries = ['/protected'] } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('RouteGuard', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, user: null });
    useWorkspaceStore.setState({ currentOrgId: null, orgList: [] });
  });

  it('should redirect to login when not authenticated', () => {
    renderWithProviders(
      <Routes>
        <Route element={<RouteGuard />}>
          <Route path="/protected" element={<div>Protected Content</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>,
    );

    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should show 403 when user lacks required role', () => {
    useAuthStore.setState({
      accessToken: 'token-123',
      user: { id: '1', email: 'test@test.com', name: 'Test', role: 'AGENCY_OPERATOR', status: 'active' },
    });
    useWorkspaceStore.setState({ currentOrgId: 'org-1' });

    renderWithProviders(
      <Routes>
        <Route element={<RouteGuard requiredRoles={['SYSTEM_ADMIN']} />}>
          <Route path="/protected" element={<div>Admin Content</div>} />
        </Route>
      </Routes>,
    );

    expect(screen.getByText('접근 권한이 없습니다')).toBeInTheDocument();
    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
  });

  it('should show workspace warning when no org selected', () => {
    useAuthStore.setState({
      accessToken: 'token-123',
      user: { id: '1', email: 'test@test.com', name: 'Test', role: 'AGENCY_MANAGER', status: 'active' },
    });
    // currentOrgId is null

    renderWithProviders(
      <Routes>
        <Route element={<RouteGuard />}>
          <Route path="/protected" element={<div>Protected Content</div>} />
        </Route>
      </Routes>,
    );

    expect(screen.getByText('워크스페이스를 선택하세요')).toBeInTheDocument();
  });

  it('should render children when authenticated with role and workspace', () => {
    useAuthStore.setState({
      accessToken: 'token-123',
      user: { id: '1', email: 'test@test.com', name: 'Test', role: 'AGENCY_MANAGER', status: 'active' },
    });
    useWorkspaceStore.setState({ currentOrgId: 'org-1' });

    renderWithProviders(
      <Routes>
        <Route element={<RouteGuard requiredRoles={['AGENCY_MANAGER', 'SYSTEM_ADMIN']} />}>
          <Route path="/protected" element={<div>Protected Content</div>} />
        </Route>
      </Routes>,
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('should render children when no specific roles required', () => {
    useAuthStore.setState({
      accessToken: 'token-123',
      user: { id: '1', email: 'test@test.com', name: 'Test', role: 'CLIENT_DIRECTOR', status: 'active' },
    });
    useWorkspaceStore.setState({ currentOrgId: 'org-1' });

    renderWithProviders(
      <Routes>
        <Route element={<RouteGuard />}>
          <Route path="/protected" element={<div>Any Role Content</div>} />
        </Route>
      </Routes>,
    );

    expect(screen.getByText('Any Role Content')).toBeInTheDocument();
  });
});
