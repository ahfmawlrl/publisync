import * as Sentry from '@sentry/react';

/** Initialize Sentry — call once in main.tsx before React renders. */
export function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    tracesSampleRate: import.meta.env.DEV ? 1.0 : 0.1,
    sendDefaultPii: false,
    beforeSend(event) {
      if (event.user) {
        delete event.user.email;
        delete event.user.ip_address;
      }
      return event;
    },
    ignoreErrors: [
      'ResizeObserver loop',
      'Network Error',
      'AbortError',
    ],
  });
}
