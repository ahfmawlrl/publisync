import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import { useWorkspaceStore } from '@/shared/stores/useWorkspaceStore';

interface WorkspaceItem {
  id: string;
  name: string;
  slug: string;
  role: string;
  is_primary: boolean;
}

export function useWorkspace() {
  const { currentOrgId, setCurrentOrg, setOrgList } = useWorkspaceStore();

  const query = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<WorkspaceItem[]>>('/workspaces');
      return res.data.data;
    },
  });

  // Auto-select primary org on first load
  useEffect(() => {
    if (query.data && query.data.length > 0) {
      setOrgList(query.data.map((w) => ({ id: w.id, name: w.name, slug: w.slug })));
      if (!currentOrgId) {
        const primary = query.data.find((w) => w.is_primary) || query.data[0];
        setCurrentOrg(primary.id);
      }
    }
  }, [query.data, currentOrgId, setCurrentOrg, setOrgList]);

  return {
    workspaces: query.data || [],
    currentOrgId,
    switchWorkspace: setCurrentOrg,
    isLoading: query.isLoading,
  };
}
