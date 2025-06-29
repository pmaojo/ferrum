import { test, expect } from '@playwright/test';

test('validate and compile yaml', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'grafo.yaml' }).click();
  const editor = page.locator('.monaco-editor textarea');
  await editor.fill('module: demo');

  await page.route('http://localhost:8001/validate/yaml', route => {
    route.fulfill({ status: 200, body: JSON.stringify({ valid: true }) });
  });
  const dialogPromise = page.waitForEvent('dialog');
  await page.getByRole('button', { name: /^Validate$/ }).click();
  const dialog = await dialogPromise;
  expect(dialog.message()).toContain('YAML válido');
  await dialog.dismiss();

  let compileCalled = false;
  await page.route('http://localhost:3001/compile', async route => {
    compileCalled = true;
    await route.fulfill({ status: 200, body: '' });
  });
  await Promise.all([
    page.waitForRequest('http://localhost:3001/compile'),
    page.getByRole('button', { name: /^Compile$/ }).click(),
  ]);
  expect(compileCalled).toBe(true);
});
