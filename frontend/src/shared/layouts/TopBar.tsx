import { BellOutlined, LogoutOutlined, MoonOutlined, SettingOutlined, SunOutlined, UserOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { Avatar, Badge, Button, Divider, Dropdown, Layout, Select, Tag, Tooltip, Typography } from 'antd';
import type { MenuProps } from 'antd';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';

import NotificationDrawer from '@/features/notifications/components/NotificationDrawer';
import { useUnreadCount } from '@/features/notifications/hooks/useNotifications';
import SearchBar from '@/shared/components/SearchBar';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useUiStore } from '@/shared/stores/useUiStore';
import { useWorkspace } from '@/shared/hooks/useWorkspace';
import type { Role } from '@/shared/types';

const { Header } = Layout;
const { Text } = Typography;

const ROLE_LABELS: Record<string, string> = {
  SYSTEM_ADMIN: '시스템 관리자',
  AGENCY_MANAGER: '수탁업체 관리자',
  AGENCY_OPERATOR: '수탁업체 실무자',
  CLIENT_DIRECTOR: '위탁기관 담당자',
};

const ROLE_COLORS: Record<string, string> = {
  SYSTEM_ADMIN: 'red',
  AGENCY_MANAGER: 'blue',
  AGENCY_OPERATOR: 'green',
  CLIENT_DIRECTOR: 'orange',
};

interface TopBarProps {
  isMobile?: boolean;
}

export default function TopBar({ isMobile = false }: TopBarProps) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);
  const collapsed = useUiStore((s) => s.sidebarCollapsed);

  const queryClient = useQueryClient();
  const { workspaces, currentOrgId, switchWorkspace } = useWorkspace();
  const hasValidWorkspace = !!currentOrgId && currentOrgId !== 'all';
  const { data: unread } = useUnreadCount(hasValidWorkspace);

  const handleSwitchWorkspace = useCallback(
    (orgId: string) => {
      if (orgId === currentOrgId) return;
      switchWorkspace(orgId);
      // 워크스페이스 전환 시 workspaces 쿼리를 제외한 모든 캐시 무효화
      queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] !== 'workspaces',
      });
    },
    [currentOrgId, switchWorkspace, queryClient],
  );
  const [drawerOpen, setDrawerOpen] = useState(false);

  const unreadCount = unread?.count ?? 0;

  const isAgencyRole = (user?.role as Role) === 'AGENCY_MANAGER' || (user?.role as Role) === 'AGENCY_OPERATOR';

  const workspaceOptions = useMemo(() => {
    const orgOptions = workspaces.map((w) => ({ value: w.id, label: w.name }));
    if (isAgencyRole) {
      return [{ value: 'all', label: '전체 기관' }, ...orgOptions];
    }
    return orgOptions;
  }, [workspaces, isAgencyRole]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const profileItems: MenuProps['items'] = [
    {
      key: 'user-info',
      label: (
        <div style={{ padding: '4px 0' }}>
          <Text strong>{user?.name || ''}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>{user?.email || ''}</Text>
        </div>
      ),
      disabled: true,
    },
    {
      key: 'role',
      label: (
        <Tag color={ROLE_COLORS[user?.role || '']}>
          {ROLE_LABELS[user?.role || ''] || user?.role}
        </Tag>
      ),
      disabled: true,
    },
    { type: 'divider' },
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '내 정보',
      disabled: true,
    },
    {
      key: 'notification-settings',
      icon: <SettingOutlined />,
      label: '알림 설정',
      onClick: () => navigate('/settings/notifications'),
    },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '로그아웃', onClick: handleLogout, danger: true },
  ];

  return (
    <>
      <Header
        className="flex items-center justify-between border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900"
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          left: isMobile ? 0 : collapsed ? 64 : 240,
          zIndex: 9,
          height: 64,
          padding: isMobile ? '0 12px' : '0 24px',
          transition: 'left 0.2s',
        }}
      >
        {/* ── Left: Workspace Switcher + Search ── */}
        <div className="flex items-center gap-3">
          <Select
            value={currentOrgId || undefined}
            onChange={handleSwitchWorkspace}
            placeholder="워크스페이스 선택"
            style={{ minWidth: isMobile ? 120 : 180 }}
            options={workspaceOptions}
          />
          {!isMobile && <SearchBar />}
        </div>

        {/* ── Right: Theme · Notifications · Profile ── */}
        <div className="flex items-center gap-1">
          {/* Theme toggle */}
          <Tooltip title={theme === 'dark' ? '라이트 모드' : '다크 모드'}>
            <Button
              type="text"
              size="large"
              icon={theme === 'dark' ? <SunOutlined style={{ fontSize: 18, color: '#faad14' }} /> : <MoonOutlined style={{ fontSize: 18, color: '#722ed1' }} />}
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              aria-label="테마 전환"
            />
          </Tooltip>

          {/* Notification bell with badge */}
          <Tooltip title="알림">
            <Badge count={unreadCount} size="small" offset={[-4, 4]}>
              <Button
                type="text"
                size="large"
                icon={<BellOutlined style={{ fontSize: 18, color: '#1677ff' }} />}
                aria-label={`알림 ${unreadCount > 0 ? `${unreadCount}건 미읽음` : ''}`}
                onClick={() => setDrawerOpen(true)}
              />
            </Badge>
          </Tooltip>

          {/* Vertical divider */}
          <Divider type="vertical" style={{ height: 24, margin: '0 4px' }} />

          {/* Profile dropdown */}
          <Dropdown menu={{ items: profileItems }} trigger={['click']} placement="bottomRight">
            <div className="flex items-center gap-2 cursor-pointer rounded-md px-2 py-1 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800">
              <Avatar
                size={32}
                style={{ backgroundColor: ROLE_COLORS[user?.role || ''] === 'blue' ? '#1677ff' : undefined }}
              >
                {user?.name?.[0] || 'U'}
              </Avatar>
              {!isMobile && (
                <span className="flex flex-col leading-tight">
                  <Text strong style={{ fontSize: 13, lineHeight: '18px' }}>{user?.name}</Text>
                  <Text type="secondary" style={{ fontSize: 11, lineHeight: '14px' }}>
                    {ROLE_LABELS[user?.role || ''] || ''}
                  </Text>
                </span>
              )}
            </div>
          </Dropdown>
        </div>
      </Header>

      <NotificationDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
