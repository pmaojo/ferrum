import { test, expect } from '@playwright/test';

test('visual editor shows nodes and edges', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'grafo.yaml' }).click();
  const yaml = [
    'module: m',
    'nodes:',
    '  - id: a',
    '    type: usecase',
    '  - id: b',
    '    type: adapter',
    '    depends_on: [a]',
  ].join('\n');
  await page.locator('.monaco-editor textarea').fill(yaml);
  await page.getByRole('button', { name: 'Visual' }).click();
  await expect(page.locator('.react-flow__node')).toHaveCount(2);
  await expect(page.locator('.react-flow__edge-path')).toHaveCount(1);
});
