import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UiState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  modalStack: string[];
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  pushModal: (id: string) => void;
  popModal: () => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      theme: 'light',
      modalStack: [],
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
      pushModal: (id) => set((s) => ({ modalStack: [...s.modalStack, id] })),
      popModal: () => set((s) => ({ modalStack: s.modalStack.slice(0, -1) })),
    }),
    { name: 'publisync-ui', partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed, theme: s.theme }) },
  ),
);
