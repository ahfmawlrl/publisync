import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { createElement, type ReactNode } from 'react';

import { useSSE } from './useSSE';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useWorkspaceStore } from '@/shared/stores/useWorkspaceStore';

// ── EventSource mock ────────────────────────────────────
type Listener = (event: MessageEvent | Event) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];

  url: string;
  readyState = 0;
  onerror: ((ev: Event) => void) | null = null;
  private listeners: Record<string, Listener[]> = {};

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener) {
    if (!this.listeners[type]) this.listeners[type] = [];
    this.listeners[type].push(listener);
  }

  removeEventListener(type: string, listener: Listener) {
    this.listeners[type] = (this.listeners[type] || []).filter((l) => l !== listener);
  }

  close = vi.fn();

  // Test helper: fire an event
  _emit(type: string, data?: unknown) {
    (this.listeners[type] || []).forEach((l) =>
      l(new MessageEvent(type, { data: data !== undefined ? JSON.stringify(data) : undefined })),
    );
  }

  _emitError() {
    if (this.onerror) this.onerror(new Event('error'));
  }
}

vi.stubGlobal('EventSource', MockEventSource);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('useSSE', () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    useAuthStore.setState({ accessToken: null, user: null });
    useWorkspaceStore.setState({ currentOrgId: null });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should start disconnected when no auth or workspace', () => {
    const { result } = renderHook(() => useSSE(), {
      wrapper: createWrapper(),
    });
    expect(result.current.status).toBe('disconnected');
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it('should start disconnected when disabled', () => {
    useAuthStore.setState({ accessToken: 'tok', user: { id: '1', email: '', name: '', role: 'AM', status: 'active' } });
    useWorkspaceStore.setState({ currentOrgId: 'org-1' });

    const { result } = renderHook(() => useSSE({ enabled: false }), {
      wrapper: createWrapper(),
    });
    expect(result.current.status).toBe('disconnected');
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it('should connect when auth and workspace are available', () => {
    useAuthStore.setState({ accessToken: 'tok', user: { id: '1', email: '', name: '', role: 'AM', status: 'active' } });
    useWorkspaceStore.setState({ currentOrgId: 'org-1' });

    const { result } = renderHook(() => useSSE(), {
      wrapper: createWrapper(),
    });

    expect(MockEventSource.instances).toHaveLength(1);
    expect(result.current.status).toBe('connecting');

    // Simulate 'connected' event
    act(() => {
      MockEventSource.instances[0]._emit('connected');
    });
    expect(result.current.status).toBe('connected');
  });

  it('should call onEvent callback on message', () => {
    useAuthStore.setState({ accessToken: 'tok', user: { id: '1', email: '', name: '', role: 'AM', status: 'active' } });
    useWorkspaceStore.setState({ currentOrgId: 'org-1' });

    const onEvent = vi.fn();
    renderHook(() => useSSE({ onEvent }), {
      wrapper: createWrapper(),
    });

    const es = MockEventSource.instances[0];
    act(() => {
      es._emit('message', { event: 'notification', id: '123' });
    });

    expect(onEvent).toHaveBeenCalledWith({ event: 'notification', id: '123' });
  });

  it('should close connection on unmount', () => {
    useAuthStore.setState({ accessToken: 'tok', user: { id: '1', email: '', name: '', role: 'AM', status: 'active' } });
    useWorkspaceStore.setState({ currentOrgId: 'org-1' });

    const { unmount } = renderHook(() => useSSE(), {
      wrapper: createWrapper(),
    });

    const es = MockEventSource.instances[0];
    unmount();
    expect(es.close).toHaveBeenCalled();
  });
});
