import {
  BarChart3,
  Bell,
  Calendar,
  CheckSquare,
  CircleHelp,
  ClipboardList,
  FileBarChart2,
  FolderOpen,
  Globe,
  History,
  LayoutDashboard,
  Link2,
  MessageSquare,
  PenLine,
  ScrollText,
  Settings,
  ShieldAlert,
  SquarePen,
  Target,
  Trophy,
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
  dangerous_comments: number;
}

const SA: Role = 'SYSTEM_ADMIN';
const AM: Role = 'AGENCY_MANAGER';
const AO: Role = 'AGENCY_OPERATOR';
const CD: Role = 'CLIENT_DIRECTOR';
const ALL_ROLES: Role[] = [SA, AM, AO, CD];

const ROLE_MENUS: Record<string, Role[]> = {
  // 대시보드
  '/': ALL_ROLES,
  // 콘텐츠 그룹
  '/contents/create': [AM, AO],
  '/contents': [AM, AO, CD],
  '/approvals': [AM, AO, CD],
  '/calendar': [AM, AO, CD],
  // 댓글 관리 그룹
  '/comments': [AM, AO, CD],
  '/comments/dangerous': [AM, AO, CD],
  '/comments/reply-templates': [AM, AO],
  // 미디어
  '/media': [AM, AO, CD],
  // 분석·리포트 그룹
  '/analytics': [AM, AO, CD],
  '/analytics/prediction': [AM, AO, CD],
  '/reports': [AM, AO, CD],
  '/analytics/sentiment': [AM, AO, CD],
  '/analytics/benchmark': [AM, AO, CD],
  // 채널 관리 그룹
  '/channels': [SA, AM],
  '/channels/history': [SA, AM],
  // 설정 그룹
  '/users': [SA, AM],
  '/approvals/settings': [SA, AM, CD],
  '/settings/notifications': ALL_ROLES,
  '/audit-logs': [SA, AM, CD],
  // 도움말
  '/help': ALL_ROLES,
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

  const mainItems: MenuProps['items'] = [
    // ── 대시보드 (독립) ──
    { key: '/', icon: <LayoutDashboard size={18} />, label: '대시보드' },

    // ── 콘텐츠 그룹 ──
    {
      type: 'group',
      label: collapsed ? null : '콘텐츠',
      children: [
        { key: '/contents/create', icon: <SquarePen size={18} />, label: '새 콘텐츠 작성' },
        { key: '/contents', icon: <ClipboardList size={18} />, label: '콘텐츠 목록' },
        {
          key: '/approvals',
          icon: <CheckSquare size={18} />,
          label: collapsed
            ? '승인 대기'
            : <BadgeLabel label="승인 대기" count={badges?.pending_approvals ?? 0} />,
        },
        { key: '/calendar', icon: <Calendar size={18} />, label: '캘린더' },
      ],
    },

    // ── 댓글 관리 그룹 ──
    {
      type: 'group',
      label: collapsed ? null : '댓글 관리',
      children: [
        {
          key: '/comments',
          icon: <MessageSquare size={18} />,
          label: collapsed
            ? '통합 댓글함'
            : <BadgeLabel label="통합 댓글함" count={badges?.unread_comments ?? 0} />,
        },
        {
          key: '/comments/dangerous',
          icon: <ShieldAlert size={18} />,
          label: collapsed
            ? '위험 댓글'
            : <BadgeLabel label="위험 댓글" count={badges?.dangerous_comments ?? 0} />,
        },
        { key: '/comments/reply-templates', icon: <PenLine size={18} />, label: '답글 템플릿 관리' },
      ],
    },

    // ── 미디어 (독립) ──
    { key: '/media', icon: <FolderOpen size={18} />, label: '미디어 라이브러리' },

    // ── 분석·리포트 그룹 ──
    {
      type: 'group',
      label: collapsed ? null : '분석·리포트',
      children: [
        { key: '/analytics', icon: <BarChart3 size={18} />, label: '성과 분석' },
        { key: '/analytics/prediction', icon: <Target size={18} />, label: '성과 예측' },
        { key: '/reports', icon: <FileBarChart2 size={18} />, label: '운영 리포트' },
        { key: '/analytics/sentiment', icon: <Globe size={18} />, label: '여론 동향' },
        { key: '/analytics/benchmark', icon: <Trophy size={18} />, label: '벤치마크 분석' },
      ],
    },

    // ── 채널 관리 그룹 ──
    {
      type: 'group',
      label: collapsed ? null : '채널 관리',
      children: [
        { key: '/channels', icon: <Link2 size={18} />, label: '연동 계정' },
        { key: '/channels/history', icon: <History size={18} />, label: '연동 이력' },
      ],
    },

    // ── 설정 그룹 ──
    {
      type: 'group',
      label: collapsed ? null : '설정',
      children: [
        { key: '/users', icon: <Users size={18} />, label: '사용자·권한' },
        { key: '/approvals/settings', icon: <Settings size={18} />, label: '승인 워크플로우 설정' },
        { key: '/settings/notifications', icon: <Bell size={18} />, label: '알림 설정' },
        { key: '/audit-logs', icon: <ScrollText size={18} />, label: '감사 로그' },
      ],
    },
  ];

  const helpItems: MenuProps['items'] = [
    { key: '/help', icon: <CircleHelp size={18} />, label: '도움말', style: { opacity: 0.7 } },
  ];

  // ── RBAC 필터링 (그룹 내 children 재귀 필터 + 빈 그룹 제거) ──
  function filterByRole(items: MenuProps['items']): MenuProps['items'] {
    return items
      ?.map((item) => {
        if (!item) return null;
        if ('type' in item && item.type === 'group') {
          const children = item.children?.filter((child) => {
            if (!child || !('key' in child)) return false;
            const allowed = ROLE_MENUS[child.key as string];
            return allowed && userRole && allowed.includes(userRole);
          });
          return children?.length ? { ...item, children } : null;
        }
        if ('key' in item) {
          const allowed = ROLE_MENUS[item.key as string];
          return allowed && userRole && allowed.includes(userRole) ? item : null;
        }
        return null;
      })
      .filter(Boolean) as MenuProps['items'];
  }

  const filteredMainItems = filterByRole(mainItems);
  const filteredHelpItems = filterByRole(helpItems);

  const handleClick: MenuProps['onClick'] = ({ key }) => navigate(key);

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={toggleSidebar}
      width={240}
      className="!fixed left-0 top-0 bottom-0 z-10"
      style={{ overflow: 'hidden', height: '100vh' }}
    >
      <nav
        aria-label="메인 네비게이션"
        style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
      >
        <div className="flex h-16 items-center justify-center">
          <span className="text-lg font-bold text-white">
            {collapsed ? 'PS' : 'PubliSync'}
          </span>
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={filteredMainItems}
            onClick={handleClick}
          />
        </div>
        {filteredHelpItems && filteredHelpItems.length > 0 && (
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', padding: '4px 0' }}>
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={[location.pathname]}
              items={filteredHelpItems}
              onClick={handleClick}
            />
          </div>
        )}
      </nav>
    </Sider>
  );
}
