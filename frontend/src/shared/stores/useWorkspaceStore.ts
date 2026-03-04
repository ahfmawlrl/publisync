import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Organization {
  id: string;
  name: string;
  slug: string;
}

interface WorkspaceState {
  currentOrgId: string | null;
  orgList: Organization[];
  setCurrentOrg: (orgId: string) => void;
  setOrgList: (orgs: Organization[]) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      currentOrgId: null,
      orgList: [],
      setCurrentOrg: (orgId) => set({ currentOrgId: orgId }),
      setOrgList: (orgs) => set({ orgList: orgs }),
    }),
    { name: 'publisync-workspace' },
  ),
);
