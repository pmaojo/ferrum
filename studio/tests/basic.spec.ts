import { test, expect } from '@playwright/test';

test('homepage has all tabs', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: /^Init$/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'grafo.yaml' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Prompt' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Visual' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'AI Scaffold' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'AI Team' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Docs' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Output' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Preview' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Tools' })).toBeVisible();
});
