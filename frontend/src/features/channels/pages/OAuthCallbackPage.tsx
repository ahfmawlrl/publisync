import { useEffect } from 'react';
import { Spin, Typography } from 'antd';

const { Text } = Typography;

/**
 * OAuth callback page — opened as popup by ChannelsPage.
 * Extracts `code` and `state` from URL params, sends to opener via postMessage, then closes.
 */
export default function OAuthCallbackPage() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    const error = params.get('error');

    if (window.opener) {
      window.opener.postMessage(
        { type: 'OAUTH_CALLBACK', code, state, error },
        window.location.origin,
      );
      // Close popup after short delay
      setTimeout(() => window.close(), 500);
    }
  }, []);

  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4">
      <Spin size="large" />
      <Text type="secondary">인증 처리 중...</Text>
    </div>
  );
}
