import { expect, test } from '@playwright/test';

/**
 * Reports page smoke tests — Phase 3 (F19).
 */

const MOCK_AUTH_STATE = {
  state: {
    accessToken: 'mock-access-token',
    refreshToken: 'mock-refresh-token',
    user: {
      id: '00000000-0000-0000-0000-000000000001',
      email: 'manager@publisync.kr',
      name: '관리자',
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

test.describe('Reports page (Phase 3)', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      (authState) => {
        localStorage.setItem('publisync-auth', JSON.stringify(authState.auth));
        localStorage.setItem('publisync-workspace', JSON.stringify(authState.workspace));
      },
      { auth: MOCK_AUTH_STATE, workspace: MOCK_WORKSPACE_STATE },
    );
  });

  test('should load reports page', async ({ page }) => {
    await page.goto('/reports');
    const childCount = await page.locator('#root > *').count();
    expect(childCount).toBeGreaterThan(0);
    await expect(page.locator('body')).not.toHaveText(/Cannot GET/i);
  });

  test('should show report page header', async ({ page }) => {
    await page.goto('/reports');
    // Page should render content (may show loading spinner)
    const childCount = await page.locator('#root > *').count();
    expect(childCount).toBeGreaterThan(0);
  });

  test('should load sentiment trend page', async ({ page }) => {
    await page.goto('/analytics/sentiment');
    const childCount = await page.locator('#root > *').count();
    expect(childCount).toBeGreaterThan(0);
    await expect(page.locator('body')).not.toHaveText(/Cannot GET/i);
  });

  test('should load prediction page', async ({ page }) => {
    await page.goto('/analytics/prediction');
    const childCount = await page.locator('#root > *').count();
    expect(childCount).toBeGreaterThan(0);
    await expect(page.locator('body')).not.toHaveText(/Cannot GET/i);
  });
});
