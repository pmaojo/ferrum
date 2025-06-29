import { test, expect } from '@playwright/test';

test('docs and output tabs show placeholders', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Docs' }).click();
  await expect(page.locator('.prose')).toBeVisible();
  await page.getByRole('button', { name: 'Output' }).click();
  await expect(page.locator('pre')).toBeVisible();
});
