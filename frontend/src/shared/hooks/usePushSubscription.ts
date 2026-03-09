/**
 * usePushSubscription — Web Push subscription management hook (Phase 1-B, F13).
 *
 * Handles Service Worker registration, push subscription lifecycle,
 * and syncing subscription data to the backend.
 */

import { useCallback, useEffect, useState } from 'react';

import apiClient from '@/shared/api/client';

const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY || '';

/** Convert URL-safe base64 VAPID key to Uint8Array for applicationServerKey */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export type PushStatus = 'unsupported' | 'denied' | 'prompt' | 'subscribed' | 'unsubscribed';

interface UsePushSubscriptionReturn {
  status: PushStatus;
  subscribe: () => Promise<boolean>;
  unsubscribe: () => Promise<boolean>;
  isSupported: boolean;
}

export function usePushSubscription(): UsePushSubscriptionReturn {
  const [status, setStatus] = useState<PushStatus>('unsupported');

  const isSupported =
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    !!VAPID_PUBLIC_KEY;

  // Check initial state
  useEffect(() => {
    if (!isSupported) {
      setStatus('unsupported');
      return;
    }

    const checkStatus = async () => {
      const permission = Notification.permission;
      if (permission === 'denied') {
        setStatus('denied');
        return;
      }

      try {
        const registration = await navigator.serviceWorker.getRegistration('/sw.js');
        if (!registration) {
          setStatus('unsubscribed');
          return;
        }

        const subscription = await registration.pushManager.getSubscription();
        setStatus(subscription ? 'subscribed' : 'unsubscribed');
      } catch {
        setStatus('unsubscribed');
      }
    };

    checkStatus();
  }, [isSupported]);

  const subscribe = useCallback(async (): Promise<boolean> => {
    if (!isSupported) return false;

    try {
      // Register Service Worker
      const registration = await navigator.serviceWorker.register('/sw.js');
      await navigator.serviceWorker.ready;

      // Request notification permission
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        setStatus('denied');
        return false;
      }

      // Subscribe to push
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY).buffer as ArrayBuffer,
      });

      // Send subscription to backend
      const subscriptionJSON = subscription.toJSON();
      await apiClient.put('/notification-settings', {
        push_subscription: subscriptionJSON,
        channels: {
          web: { enabled: true },
          email: { enabled: true },
          telegram: { enabled: false },
          webPush: { enabled: true },
        },
      });

      setStatus('subscribed');
      return true;
    } catch (error) {
      console.error('Push subscription failed:', error);
      return false;
    }
  }, [isSupported]);

  const unsubscribe = useCallback(async (): Promise<boolean> => {
    try {
      const registration = await navigator.serviceWorker.getRegistration('/sw.js');
      if (!registration) return true;

      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
      }

      // Clear subscription on backend
      await apiClient.put('/notification-settings', {
        push_subscription: null,
        channels: {
          web: { enabled: true },
          email: { enabled: true },
          telegram: { enabled: false },
          webPush: { enabled: false },
        },
      });

      setStatus('unsubscribed');
      return true;
    } catch (error) {
      console.error('Push unsubscribe failed:', error);
      return false;
    }
  }, []);

  return { status, subscribe, unsubscribe, isSupported };
}
