import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp, theme } from 'antd';
import koKR from 'antd/locale/ko_KR';
import { useEffect } from 'react';
import { RouterProvider } from 'react-router';

import { router } from './router';
import { useUiStore } from '@/shared/stores/useUiStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 2,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  },
});

export default function App() {
  const isDark = useUiStore((s) => s.theme === 'dark');

  // Sync dark mode class + data-theme attribute on <html>
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={koKR}
        theme={{
          algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorPrimary: '#1677ff',
            borderRadius: 6,
          },
        }}
      >
        <AntApp>
          <RouterProvider router={router} />
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
