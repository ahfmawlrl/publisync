import { expect, test } from '@playwright/test';

/**
 * Navigation smoke tests — verifies that all main routes are reachable.
 * These tests mock authentication by injecting auth state into localStorage.
 */

const MOCK_AUTH_STATE = {
  state: {
    accessToken: 'mock-access-token',
    refreshToken: 'mock-refresh-token',
    user: {
      id: '00000000-0000-0000-0000-000000000001',
      email: 'test@publisync.kr',
      name: '테스트 사용자',
      role: 'AGENCY_MANAGER',
      status: 'ACTIVE',
    },
  },
  version: 0,
};

const MOCK_WORKSPACE_STATE = {
  state: {
    currentOrgId: '00000000-0000-0000-0000-000000000001',
    workspaces: [{ id: '00000000-0000-0000-0000-000000000001', name: '테스트 기관' }],
  },
  version: 0,
};

test.describe('Protected route navigation (smoke)', () => {
  test.beforeEach(async ({ page }) => {
    // Inject mock auth state before navigating
    await page.addInitScript((authState) => {
      localStorage.setItem('publisync-auth', JSON.stringify(authState.auth));
      localStorage.setItem('publisync-workspace', JSON.stringify(authState.workspace));
    }, { auth: MOCK_AUTH_STATE, workspace: MOCK_WORKSPACE_STATE });
  });

  const routes = [
    { path: '/', name: 'Dashboard' },
    { path: '/contents', name: 'Contents list' },
    { path: '/contents/create', name: 'Content create' },
    { path: '/approvals', name: 'Approvals list' },
    { path: '/comments', name: 'Comments list' },
    { path: '/comments/dangerous', name: 'Dangerous comments' },
    { path: '/channels', name: 'Channels' },
    { path: '/analytics', name: 'Analytics' },
    { path: '/notifications', name: 'Notifications' },
    { path: '/audit-logs', name: 'Audit logs' },
    { path: '/users', name: 'Users' },
    // Phase 2 routes
    { path: '/calendar', name: 'Calendar' },
    { path: '/media', name: 'Media library' },
    { path: '/ai/subtitle-editor/00000000-0000-0000-0000-000000000001', name: 'Subtitle editor' },
    { path: '/ai/shortform-editor/00000000-0000-0000-0000-000000000001', name: 'Shortform editor' },
    // Phase 3 routes
    { path: '/reports', name: 'Reports' },
    { path: '/analytics/sentiment', name: 'Sentiment trend' },
    { path: '/analytics/prediction', name: 'Prediction' },
    // Phase 4 routes
    { path: '/analytics/benchmark', name: 'Benchmark' },
  ];

  for (const route of routes) {
    test(`should load ${route.name} page at ${route.path}`, async ({ page }) => {
      await page.goto(route.path);

      // Page should load without fatal errors — check that the root div has content
      const rootContent = await page.locator('#root').textContent();
      expect(rootContent).toBeTruthy();

      // Should not show a blank error page
      await expect(page.locator('body')).not.toHaveText(/Cannot GET/i);
    });
  }
});
