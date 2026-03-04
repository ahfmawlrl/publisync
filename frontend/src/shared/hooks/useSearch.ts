import { useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { PaginatedResponse } from '@/shared/api/types';
import { useDebounce } from './useDebounce';

export interface SearchResultItem {
  id: string;
  type: string;
  title: string;
  snippet: string | null;
  status: string;
  created_at: string;
}

export function useSearch(query: string) {
  const debouncedQuery = useDebounce(query, 300);

  return useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<SearchResultItem>>('/search', {
        params: { q: debouncedQuery, limit: 10 },
      });
      return res.data;
    },
    enabled: debouncedQuery.length >= 2,
    staleTime: 30_000,
  });
}
