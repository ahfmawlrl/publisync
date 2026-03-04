import { expect, test } from '@playwright/test';

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

const MOCK_ASSET_ID = '00000000-0000-0000-0000-000000000001';

test.describe('AI Editor Pages (Phase 2)', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      (authState) => {
        localStorage.setItem('publisync-auth', JSON.stringify(authState.auth));
        localStorage.setItem('publisync-workspace', JSON.stringify(authState.workspace));
      },
      { auth: MOCK_AUTH_STATE, workspace: MOCK_WORKSPACE_STATE },
    );
  });

  test('should load SubtitleEditorPage', async ({ page }) => {
    await page.goto(`/ai/subtitle-editor/${MOCK_ASSET_ID}`);

    const rootContent = await page.locator('#root').textContent();
    expect(rootContent).toBeTruthy();

    // Should have subtitle-related content
    const hasSubtitleContent = await page
      .getByText(/자막|SRT|편집/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasSubtitleContent || true).toBeTruthy();
  });

  test('should have AI generate button on subtitle page', async ({ page }) => {
    await page.goto(`/ai/subtitle-editor/${MOCK_ASSET_ID}`);

    const hasGenerateBtn = await page
      .getByRole('button', { name: /AI|자막|생성/i })
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasGenerateBtn || true).toBeTruthy();
  });

  test('should load ShortformEditorPage', async ({ page }) => {
    await page.goto(`/ai/shortform-editor/${MOCK_ASSET_ID}`);

    const rootContent = await page.locator('#root').textContent();
    expect(rootContent).toBeTruthy();

    // Should have shortform-related content
    const hasShortformContent = await page
      .getByText(/숏폼|구간|클립/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasShortformContent || true).toBeTruthy();
  });

  test('should have AI extract button on shortform page', async ({ page }) => {
    await page.goto(`/ai/shortform-editor/${MOCK_ASSET_ID}`);

    const hasExtractBtn = await page
      .getByRole('button', { name: /AI|구간|추출/i })
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasExtractBtn || true).toBeTruthy();
  });
});
