import { Bell, ClipboardList, LayoutDashboard, Menu, MessageSquare } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router';

import { useUiStore } from '@/shared/stores/useUiStore';

const THEME_STYLES = {
  light: { bg: '#fff', border: '#e5e7eb', active: '#1677ff', inactive: '#8c8c8c' },
  dark: { bg: '#141414', border: '#303030', active: '#1668dc', inactive: '#6b6b6b' },
} as const;

interface TabItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  path?: string;
  action?: () => void;
}

export default function MobileTabBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const setMobileMenuOpen = useUiStore((s) => s.setMobileMenuOpen);
  const theme = useUiStore((s) => s.theme);
  const colors = THEME_STYLES[theme];

  const tabs: TabItem[] = [
    { key: '/', label: '대시보드', icon: <LayoutDashboard size={20} />, path: '/' },
    { key: '/contents', label: '콘텐츠', icon: <ClipboardList size={20} />, path: '/contents' },
    { key: '/comments', label: '댓글', icon: <MessageSquare size={20} />, path: '/comments' },
    { key: '/notifications', label: '알림', icon: <Bell size={20} />, path: '/notifications' },
    { key: 'more', label: '더보기', icon: <Menu size={20} />, action: () => setMobileMenuOpen(true) },
  ];

  const isActive = (key: string) => {
    if (key === '/') return location.pathname === '/';
    return location.pathname.startsWith(key);
  };

  const handleClick = (tab: TabItem) => {
    if (tab.action) {
      tab.action();
    } else if (tab.path) {
      navigate(tab.path);
    }
  };

  return (
    <nav
      aria-label="모바일 네비게이션"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 56,
        backgroundColor: colors.bg,
        borderTop: `1px solid ${colors.border}`,
        zIndex: 20,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-around',
      }}
    >
      {tabs.map((tab) => {
        const active = isActive(tab.key);
        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => handleClick(tab)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 2,
              flex: 1,
              height: '100%',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              color: active ? colors.active : colors.inactive,
              fontSize: 11,
              fontWeight: active ? 600 : 400,
              padding: 0,
              transition: 'color 0.2s',
            }}
            aria-current={active ? 'page' : undefined}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
