import { useQuery } from '@tanstack/react-query';
import type { Template } from '@shared/schema';
import {
  getTemplateCategories,
  searchTemplates,
} from '@/services/templateService';

export function useTemplateCategories() {
  return useQuery<Record<string, Template[]>>({
    queryKey: ['/api/v1/templates', 'categories'],
    queryFn: getTemplateCategories,
  });
}

export function useTemplateSearch(query: string) {
  return useQuery<Template[]>({
    queryKey: ['/api/v1/templates', 'search', query],
    queryFn: () => searchTemplates(query),
    enabled: !!query,
  });
}
