import { test, expect } from '@playwright/test';

test('prompt generation updates editor', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Prompt' }).click();
  await page.fill('textarea', 'crud for user');
  await page.route('http://localhost:8001/generate-yaml', route => {
    route.fulfill({ status: 200, body: JSON.stringify({ yaml: 'module: users' }) });
  });
  await page.getByRole('button', { name: /^Generate$/ }).click();
  await page.getByRole('button', { name: 'grafo.yaml' }).click();
  const value = await page.locator('.monaco-editor textarea').inputValue();
  expect(value).toContain('module: users');
});
