import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UiState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  modalStack: string[];
  mobileMenuOpen: boolean;
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  pushModal: (id: string) => void;
  popModal: () => void;
  setMobileMenuOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      theme: 'light',
      modalStack: [],
      mobileMenuOpen: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
      pushModal: (id) => set((s) => ({ modalStack: [...s.modalStack, id] })),
      popModal: () => set((s) => ({ modalStack: s.modalStack.slice(0, -1) })),
      setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
    }),
    { name: 'publisync-ui', partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed, theme: s.theme }) },
  ),
);
