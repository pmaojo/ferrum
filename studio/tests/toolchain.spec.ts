import { test, expect } from '@playwright/test';

test('toolchain actions call cli endpoints', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Tools' }).click();

  await page.route('http://localhost:3001/dev', route => {
    route.fulfill({ status: 200, body: JSON.stringify({ output: 'dev' }) });
  });
  await page.getByRole('button', { name: /^Start$/ }).click();
  await expect(page.locator('pre')).toContainText('dev');

  await page.route('http://localhost:3001/sync', route => {
    route.fulfill({ status: 200, body: JSON.stringify({ output: 'sync' }) });
  });
  await page.getByRole('button', { name: /^Sync$/ }).click();
  await expect(page.locator('pre')).toContainText('sync');

  await page.route('http://localhost:3001/migrate', route => {
    route.fulfill({ status: 200, body: JSON.stringify({ output: 'migrate' }) });
  });
  await page.getByRole('button', { name: /^Migrate$/ }).click();
  await expect(page.locator('pre')).toContainText('migrate');
});
