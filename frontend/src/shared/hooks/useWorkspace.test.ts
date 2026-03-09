import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { createElement, type ReactNode } from 'react';

import { useWorkspace } from './useWorkspace';
import { useWorkspaceStore } from '@/shared/stores/useWorkspaceStore';

// Mock apiClient
vi.mock('@/shared/api/client', () => ({
  default: {
    get: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useWorkspace', () => {
  beforeEach(() => {
    // Reset Zustand store
    useWorkspaceStore.setState({
      currentOrgId: null,
      orgList: [],
    });
  });

  it('should return empty workspaces while loading', () => {
    const { result } = renderHook(() => useWorkspace(), {
      wrapper: createWrapper(),
    });
    expect(result.current.workspaces).toEqual([]);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.currentOrgId).toBeNull();
  });

  it('should auto-select primary workspace on load', async () => {
    const mockData = [
      { id: 'org-1', name: 'Org 1', slug: 'org-1', role: 'AM', is_primary: false },
      { id: 'org-2', name: 'Org 2', slug: 'org-2', role: 'AO', is_primary: true },
    ];

    const { default: apiClient } = await import('@/shared/api/client');
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { data: mockData },
    });

    const { result } = renderHook(() => useWorkspace(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.workspaces).toEqual(mockData);
    // Primary workspace (org-2) should be auto-selected
    expect(result.current.currentOrgId).toBe('org-2');
  });

  it('should fallback to first workspace if no primary', async () => {
    const mockData = [
      { id: 'org-1', name: 'Org 1', slug: 'org-1', role: 'AM', is_primary: false },
      { id: 'org-3', name: 'Org 3', slug: 'org-3', role: 'CD', is_primary: false },
    ];

    const { default: apiClient } = await import('@/shared/api/client');
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { data: mockData },
    });

    const { result } = renderHook(() => useWorkspace(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Should pick first workspace
    expect(result.current.currentOrgId).toBe('org-1');
  });

  it('should not override already selected workspace', async () => {
    // Pre-select a workspace
    useWorkspaceStore.setState({ currentOrgId: 'org-existing' });

    const mockData = [
      { id: 'org-1', name: 'Org 1', slug: 'org-1', role: 'AM', is_primary: true },
    ];

    const { default: apiClient } = await import('@/shared/api/client');
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { data: mockData },
    });

    const { result } = renderHook(() => useWorkspace(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Should keep existing selection
    expect(result.current.currentOrgId).toBe('org-existing');
  });

  it('should expose switchWorkspace function', () => {
    const { result } = renderHook(() => useWorkspace(), {
      wrapper: createWrapper(),
    });
    expect(typeof result.current.switchWorkspace).toBe('function');
  });
});
