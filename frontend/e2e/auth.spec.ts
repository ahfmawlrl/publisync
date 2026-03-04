import { expect, test } from '@playwright/test';

test.describe('Authentication', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /로그인/i })).toBeVisible();
    await expect(page.getByPlaceholder(/이메일/i)).toBeVisible();
    await expect(page.getByPlaceholder(/비밀번호/i)).toBeVisible();
  });

  test('should show validation error on empty submit', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: /로그인/i }).click();

    // Should show at least one validation error
    await expect(page.getByText(/입력하세요|필수/i).first()).toBeVisible();
  });

  test('should redirect unauthenticated user to login', async ({ page }) => {
    await page.goto('/');
    // Should redirect to /login
    await page.waitForURL('**/login**');
    await expect(page).toHaveURL(/\/login/);
  });

  test('should show reset password page', async ({ page }) => {
    await page.goto('/reset-password');
    await expect(page.getByRole('heading', { name: /비밀번호/i })).toBeVisible();
  });
});
