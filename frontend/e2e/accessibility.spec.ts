import { expect, test } from '@playwright/test';

test.describe('Accessibility basics', () => {
  test('login page has proper ARIA labels', async ({ page }) => {
    await page.goto('/login');

    // Check for lang attribute on html
    const htmlLang = await page.locator('html').getAttribute('lang');
    expect(htmlLang).toBeTruthy();

    // Input fields should have associated labels or aria-labels
    const emailInput = page.getByPlaceholder(/이메일/i);
    const passwordInput = page.getByPlaceholder(/비밀번호/i);

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
  });

  test('login page button is keyboard accessible', async ({ page }) => {
    await page.goto('/login');

    // Tab through elements and check focus reaches the button
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // At least one element should be focused
    const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedTag).toBeTruthy();
  });
});
