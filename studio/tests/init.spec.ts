import { test, expect } from '@playwright/test';

test('init form sends selected options', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /^Init$/ }).click();

  await page.fill('input[placeholder="project name"]', 'demo');
  await page.getByLabel('With graph database').check();
  await page.getByLabel('With PostgreSQL').check();

  let body: any = null;
  await page.route('http://localhost:3001/init', async route => {
    body = JSON.parse(route.request().postData() || '{}');
    await route.fulfill({ status: 200, body: '' });
  });

  await page.getByRole('button', { name: /^Initialize$/ }).click();
  await expect.poll(() => body?.name).toBe('demo');
  await expect.poll(() => body?.with_graph).toBe(true);
  await expect.poll(() => body?.with_db).toBe(true);
});
