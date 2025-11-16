import type { Template } from '@shared/schema';

export async function getTemplateCategories(): Promise<
  Record<string, Template[]>
> {
  const res = await fetch('/api/v1/templates/categories');
  if (!res.ok) throw new Error('Failed to fetch template categories');
  return res.json();
}

export async function searchTemplates(query: string): Promise<Template[]> {
  const res = await fetch(
    `/api/v1/templates/search?q=${encodeURIComponent(query)}`
  );
  if (!res.ok) throw new Error('Failed to search templates');
  return res.json();
}
