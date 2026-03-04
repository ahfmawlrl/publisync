import {
  BarChart3,
  Bell,
  Calendar,
  Crosshair,
  FileBarChart2,
  FileText,
  Image,
  LayoutDashboard,
  Link2,
  MessageSquare,
  ScrollText,
  Settings,
  Shield,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react';
import { Badge, Layout, Menu } from 'antd';
import { useLocation, useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import type { MenuProps } from 'antd';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useUiStore } from '@/shared/stores/useUiStore';
import { useWorkspaceStore } from '@/shared/stores/useWorkspaceStore';
import type { Role } from '@/shared/types';

const { Sider } = Layout;

interface BadgeCounts {
  pending_approvals: number;
  scheduled_posts: number;
  unread_comments: number;
  unread_notifications: number;
}

const ROLE_MENUS: Record<string, Role[]> = {
  '/': ['SYSTEM_ADMIN', 'AGENCY_MANAGER', 'AGENCY_OPERATOR', 'CLIENT_DIRECTOR'],
  '/contents': ['AGENCY_MANAGER', 'AGENCY_OPERATOR'],
  '/approvals': ['AGENCY_MANAGER', 'CLIENT_DIRECTOR'],
  '/comments': ['AGENCY_MANAGER', 'AGENCY_OPERATOR'],
  '/channels': ['AGENCY_MANAGER'],
  '/calendar': ['AGENCY_MANAGER', 'AGENCY_OPERATOR', 'CLIENT_DIRECTOR'],
  '/media': ['AGENCY_MANAGER', 'AGENCY_OPERATOR'],
  '/analytics': ['SYSTEM_ADMIN', 'AGENCY_MANAGER', 'AGENCY_OPERATOR', 'CLIENT_DIRECTOR'],
  '/analytics/sentiment': ['SYSTEM_ADMIN', 'AGENCY_MANAGER', 'AGENCY_OPERATOR', 'CLIENT_DIRECTOR'],
  '/analytics/prediction': ['SYSTEM_ADMIN', 'AGENCY_MANAGER', 'AGENCY_OPERATOR', 'CLIENT_DIRECTOR'],
  '/analytics/benchmark': ['SYSTEM_ADMIN', 'AGENCY_MANAGER', 'CLIENT_DIRECTOR'],
  '/reports': ['SYSTEM_ADMIN', 'AGENCY_MANAGER', 'CLIENT_DIRECTOR'],
  '/notifications': ['SYSTEM_ADMIN', 'AGENCY_MANAGER', 'AGENCY_OPERATOR', 'CLIENT_DIRECTOR'],
  '/audit-logs': ['SYSTEM_ADMIN', 'AGENCY_MANAGER'],
  '/users': ['SYSTEM_ADMIN', 'AGENCY_MANAGER'],
  '/settings': ['SYSTEM_ADMIN', 'AGENCY_MANAGER'],
};

function BadgeLabel({ label, count }: { label: string; count: number }) {
  return (
    <span className="flex items-center justify-between">
      {label}
      {count > 0 && <Badge count={count} size="small" />}
    </span>
  );
}

export default function Sidebar() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const userRole = useAuthStore((s) => s.user?.role) as Role | undefined;
  const currentOrgId = useWorkspaceStore((s) => s.currentOrgId);
  const navigate = useNavigate();
  const location = useLocation();

  const { data: badges } = useQuery({
    queryKey: ['badge-counts', currentOrgId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<BadgeCounts>>('/dashboard/badge-counts');
      return res.data.data;
    },
    enabled: !!currentOrgId,
    refetchInterval: 60_000,
  });

  const allItems: MenuProps['items'] = [
    { key: '/', icon: <LayoutDashboard size={18} />, label: '대시보드' },
    { key: '/contents', icon: <FileText size={18} />, label: '콘텐츠' },
    {
      key: '/approvals',
      icon: <Shield size={18} />,
      label: collapsed ? '승인' : <BadgeLabel label="승인" count={badges?.pending_approvals ?? 0} />,
    },
    {
      key: '/comments',
      icon: <MessageSquare size={18} />,
      label: collapsed ? '댓글' : <BadgeLabel label="댓글" count={badges?.unread_comments ?? 0} />,
    },
    { key: '/channels', icon: <Link2 size={18} />, label: '채널' },
    { key: '/calendar', icon: <Calendar size={18} />, label: '캘린더' },
    { key: '/media', icon: <Image size={18} />, label: '미디어' },
    { key: '/analytics', icon: <BarChart3 size={18} />, label: '성과 분석' },
    { key: '/analytics/sentiment', icon: <TrendingUp size={18} />, label: '여론 동향' },
    { key: '/analytics/prediction', icon: <Target size={18} />, label: '성과 예측' },
    { key: '/analytics/benchmark', icon: <Crosshair size={18} />, label: '벤치마크' },
    { key: '/reports', icon: <FileBarChart2 size={18} />, label: '리포트' },
    {
      key: '/notifications',
      icon: <Bell size={18} />,
      label: collapsed ? '알림' : <BadgeLabel label="알림" count={badges?.unread_notifications ?? 0} />,
    },
    { key: '/audit-logs', icon: <ScrollText size={18} />, label: '감사 로그' },
    { key: '/users', icon: <Users size={18} />, label: '사용자' },
    { key: '/settings', icon: <Settings size={18} />, label: '설정' },
  ];

  const filteredItems = allItems?.filter((item) => {
    if (!item || !('key' in item)) return false;
    const allowedRoles = ROLE_MENUS[item.key as string];
    if (!allowedRoles || !userRole) return false;
    return allowedRoles.includes(userRole);
  });

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={toggleSidebar}
      width={240}
      className="!fixed left-0 top-0 bottom-0 z-10"
      style={{ overflow: 'auto', height: '100vh' }}
    >
      <nav aria-label="메인 네비게이션">
        <div className="flex h-16 items-center justify-center">
          <span className="text-lg font-bold text-white">
            {collapsed ? 'PS' : 'PubliSync'}
          </span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={filteredItems}
          onClick={({ key }) => navigate(key)}
        />
      </nav>
    </Sider>
  );
}
