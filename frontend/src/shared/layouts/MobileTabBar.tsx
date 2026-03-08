import { Bell, ClipboardList, LayoutDashboard, Menu, MessageSquare } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router';

import { useUiStore } from '@/shared/stores/useUiStore';

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
        backgroundColor: '#fff',
        borderTop: '1px solid #e5e7eb',
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
              color: active ? '#1677ff' : '#8c8c8c',
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
