import { expect, test } from '@playwright/test';

/**
 * Contents page E2E tests.
 * Uses mock auth state to access protected routes.
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
    orgList: [{ id: '00000000-0000-0000-0000-000000000001', name: '테스트 기관', slug: 'test-org' }],
  },
  version: 0,
};

test.describe('Contents Pages', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      (authState) => {
        localStorage.setItem('publisync-auth', JSON.stringify(authState.auth));
        localStorage.setItem('publisync-workspace', JSON.stringify(authState.workspace));
      },
      { auth: MOCK_AUTH_STATE, workspace: MOCK_WORKSPACE_STATE },
    );
  });

  test('should render contents list page', async ({ page }) => {
    await page.goto('/contents');

    // Page should render without errors (React root has children)
    const childCount = await page.locator('#root > *').count();
    expect(childCount).toBeGreaterThan(0);

    // Should not be redirected to login
    await expect(page).not.toHaveURL(/\/login/);
  });

  test('should render content create page', async ({ page }) => {
    await page.goto('/contents/create');

    const childCount = await page.locator('#root > *').count();
    expect(childCount).toBeGreaterThan(0);

    await expect(page).not.toHaveURL(/\/login/);
  });

  test('should render approvals list page', async ({ page }) => {
    await page.goto('/approvals');

    const childCount = await page.locator('#root > *').count();
    expect(childCount).toBeGreaterThan(0);

    await expect(page).not.toHaveURL(/\/login/);
  });
});
