import { test, expect } from '@playwright/test';

test('ai scaffold displays generated yaml', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'AI Scaffold' }).click();
  await page.fill('textarea', 'blog app');
  await page.route('/api/ai/generate', route => {
    route.fulfill({ status: 200, body: JSON.stringify({ yaml: 'module: blog' }) });
  });
  await page.getByRole('button', { name: 'Generar' }).click();
  await expect(page.locator('pre')).toContainText('module: blog');
});
