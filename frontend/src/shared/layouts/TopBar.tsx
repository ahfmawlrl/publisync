import { BellOutlined, LogoutOutlined, MoonOutlined, SettingOutlined, SunOutlined, UserOutlined } from '@ant-design/icons';
import { Avatar, Badge, Button, Dropdown, Layout, Select, Space, Tag, Typography } from 'antd';
import type { MenuProps } from 'antd';
import { useMemo, useState } from 'react';
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

  const { workspaces, currentOrgId, switchWorkspace } = useWorkspace();
  const { data: unread } = useUnreadCount();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const isAgencyRole = (user?.role as Role) === 'AGENCY_MANAGER' || (user?.role as Role) === 'AGENCY_OPERATOR';

  /** Build workspace options — prepend "전체 기관" for agency roles (AM, AO) */
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
        <div>
          <Text strong>{user?.name || ''}</Text>
          <br />
          <Text type="secondary" className="text-xs">{user?.email || ''}</Text>
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
    { key: 'logout', icon: <LogoutOutlined />, label: '로그아웃', onClick: handleLogout },
  ];

  return (
    <>
      <Header
        className="flex items-center justify-between border-b border-gray-200 bg-white px-6 dark:border-gray-700 dark:bg-gray-900"
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
        {/* Left side: Workspace switcher + Search (desktop) / Logo (mobile) */}
        {isMobile ? (
          <Text strong className="text-base">PubliSync</Text>
        ) : (
          <Space size="middle" split={<div className="h-6 w-px bg-gray-300 dark:bg-gray-600" />}>
            <Select
              value={currentOrgId || undefined}
              onChange={switchWorkspace}
              placeholder="워크스페이스 선택"
              style={{ width: 200 }}
              options={workspaceOptions}
            />
            <SearchBar />
          </Space>
        )}

        {/* Right side */}
        <Space size="middle">
          <Button
            type="text"
            icon={theme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label="테마 전환"
          />
          <Badge count={unread?.count ?? 0} size="small">
            <Button
              type="text"
              icon={<BellOutlined />}
              aria-label="알림"
              onClick={() => setDrawerOpen(true)}
            />
          </Badge>
          <Dropdown menu={{ items: profileItems }} trigger={['click']}>
            <Space className="cursor-pointer">
              <Avatar size="small">{user?.name?.[0] || 'U'}</Avatar>
              <Text className="hidden lg:inline">{user?.name}</Text>
            </Space>
          </Dropdown>
        </Space>
      </Header>

      <NotificationDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
