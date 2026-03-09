import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useWorkspaceStore } from '@/shared/stores/useWorkspaceStore';

/** SSE connection status */
export type SSEStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'polling';

/** SSE event received from the server */
export interface SSEEvent {
  event: string;
  [key: string]: unknown;
}

interface UseSSEOptions {
  /** Whether the SSE connection should be active (default: true) */
  enabled?: boolean;
  /** Custom event handler — called for every SSE message */
  onEvent?: (event: SSEEvent) => void;
  /** Max reconnect attempts before falling back to polling (default: 5) */
  maxRetries?: number;
  /** Polling interval in ms when in fallback mode (default: 15000) */
  pollingInterval?: number;
}

/** Map SSE event types → TanStack Query keys to invalidate */
const EVENT_INVALIDATION_MAP: Record<string, string[][]> = {
  publish_started: [['contents']],
  publish_completed: [['contents'], ['dashboard']],
  publish_failed: [['contents'], ['dashboard']],
  approval_requested: [['approvals'], ['dashboard']],
  approval_completed: [['approvals'], ['contents'], ['dashboard']],
  channel_status_changed: [['channels']],
  notification: [['notifications']],
  comment_received: [['comments'], ['dashboard']],
  dangerous_comment: [['comments'], ['dashboard']],
  ai_job_completed: [['ai']],
};

export function useSSE(options: UseSSEOptions = {}) {
  const {
    enabled = true,
    onEvent,
    maxRetries = 5,
    pollingInterval = 15_000,
  } = options;

  const queryClient = useQueryClient();
  const [status, setStatus] = useState<SSEStatus>('disconnected');

  const retryCountRef = useRef(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const accessToken = useAuthStore((s) => s.accessToken);
  const orgId = useWorkspaceStore((s) => s.currentOrgId);

  // Stable refs for callbacks to avoid re-creating EventSource
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const handleInvalidation = useCallback(
    (eventType: string) => {
      const keys = EVENT_INVALIDATION_MAP[eventType];
      if (keys) {
        keys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
      }
    },
    [queryClient],
  );

  const clearPolling = useCallback(() => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    clearPolling();
    setStatus('polling');
    pollingTimerRef.current = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    }, pollingInterval);
  }, [queryClient, pollingInterval, clearPolling]);

  const closeConnection = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  useEffect(() => {
    if (!enabled || !accessToken || !orgId) {
      closeConnection();
      clearPolling();
      setStatus('disconnected');
      return;
    }

    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      closeConnection();
      clearPolling();

      const url = `/api/v1/sse/events?token=${encodeURIComponent(accessToken!)}&workspace=${encodeURIComponent(orgId!)}`;
      const es = new EventSource(url);
      eventSourceRef.current = es;
      setStatus('connecting');

      es.addEventListener('connected', () => {
        retryCountRef.current = 0;
        setStatus('connected');
      });

      es.addEventListener('message', (e) => {
        try {
          const parsed = JSON.parse(e.data) as SSEEvent;
          handleInvalidation(parsed.event);
          onEventRef.current?.(parsed);
        } catch {
          // Ignore malformed messages
        }
      });

      es.addEventListener('heartbeat', () => {
        retryCountRef.current = 0;
      });

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;
        retryCountRef.current += 1;

        if (retryCountRef.current >= maxRetries) {
          setStatus('error');
          startPolling();
          return;
        }

        // Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 30s)
        const delay = Math.min(1000 * 2 ** retryCountRef.current, 30_000);
        setStatus('disconnected');
        reconnectTimer = setTimeout(connect, delay);
      };
    }

    connect();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      closeConnection();
      clearPolling();
    };
    // Re-connect when auth or workspace changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, accessToken, orgId]);

  return { status };
}
