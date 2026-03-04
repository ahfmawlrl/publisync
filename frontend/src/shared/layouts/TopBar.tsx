import { BellOutlined, LogoutOutlined, MoonOutlined, SunOutlined } from '@ant-design/icons';
import { Avatar, Button, Dropdown, Layout, Select, Space, Typography } from 'antd';
import type { MenuProps } from 'antd';
import { useNavigate } from 'react-router';

import SearchBar from '@/shared/components/SearchBar';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useUiStore } from '@/shared/stores/useUiStore';
import { useWorkspace } from '@/shared/hooks/useWorkspace';

const { Header } = Layout;
const { Text } = Typography;

export default function TopBar() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);
  const collapsed = useUiStore((s) => s.sidebarCollapsed);

  const { workspaces, currentOrgId, switchWorkspace } = useWorkspace();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const profileItems: MenuProps['items'] = [
    { key: 'name', label: user?.name || '', disabled: true },
    { key: 'email', label: user?.email || '', disabled: true },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '로그아웃', onClick: handleLogout },
  ];

  return (
    <Header
      className="flex items-center justify-between border-b border-gray-200 bg-white px-6 dark:bg-gray-900"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        left: collapsed ? 80 : 240,
        zIndex: 9,
        height: 64,
        padding: '0 24px',
        transition: 'left 0.2s',
      }}
    >
      {/* Left side: Workspace switcher + Search */}
      <Space size="middle">
        <Select
          value={currentOrgId || undefined}
          onChange={switchWorkspace}
          placeholder="워크스페이스 선택"
          style={{ width: 200 }}
          options={workspaces.map((w) => ({ value: w.id, label: w.name }))}
        />
        <SearchBar />
      </Space>

      {/* Right side */}
      <Space size="middle">
        <Button
          type="text"
          icon={theme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label="테마 전환"
        />
        <Button type="text" icon={<BellOutlined />} aria-label="알림" />
        <Dropdown menu={{ items: profileItems }} trigger={['click']}>
          <Space className="cursor-pointer">
            <Avatar size="small">{user?.name?.[0] || 'U'}</Avatar>
            <Text className="hidden lg:inline">{user?.name}</Text>
          </Space>
        </Dropdown>
      </Space>
    </Header>
  );
}
