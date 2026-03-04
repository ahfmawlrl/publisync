import { describe, expect, it, beforeEach } from 'vitest';
import { useUiStore } from './useUiStore';

describe('useUiStore', () => {
  beforeEach(() => {
    useUiStore.setState({ sidebarCollapsed: false, theme: 'light' });
  });

  it('should toggle sidebar', () => {
    expect(useUiStore.getState().sidebarCollapsed).toBe(false);
    useUiStore.getState().toggleSidebar();
    expect(useUiStore.getState().sidebarCollapsed).toBe(true);
    useUiStore.getState().toggleSidebar();
    expect(useUiStore.getState().sidebarCollapsed).toBe(false);
  });

  it('should set theme', () => {
    useUiStore.getState().setTheme('dark');
    expect(useUiStore.getState().theme).toBe('dark');
  });
});
