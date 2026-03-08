import {
  Activity,
  BarChart3,
  Bell,
  Building2,
  Calendar,
  CheckSquare,
  CircleHelp,
  ClipboardList,
  FileBarChart2,
  FolderOpen,
  Globe,
  LayoutDashboard,
  Link2,
  MessageSquare,
  Monitor,
  PenLine,
  ScrollText,
  Settings,
  ShieldAlert,
  SquarePen,
  Target,
  Trophy,
  Users,
} from 'lucide-react';
import { Badge, Drawer, Layout, Menu } from 'antd';
import { useLocation, useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import type { MenuProps } from 'antd';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import PubliSyncLogo from '@/shared/components/PubliSyncLogo';
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
  '/channels/api-status': [SA, AM],
  // 설정 그룹
  '/settings/organizations': [SA, AM],
  '/users': [SA, AM],
  '/approvals/settings': [SA, AM, CD],
  '/settings/notifications': ALL_ROLES,
  '/audit-logs': [SA, AM, CD],
  // 시스템 관리 (SA 전용)
  '/admin': [SA],
  // 도움말
  '/help': ALL_ROLES,
};

// ── Phase-based menu visibility ──
// Change this constant to unlock menus for later phases.
type Phase = '1-A' | '1-B' | '2' | '3' | '4';
const CURRENT_PHASE: Phase = '1-A';

/** Ordered list of phases — each phase includes all prior phases */
const PHASE_ORDER: Phase[] = ['1-A', '1-B', '2', '3', '4'];

/** Menus introduced in each phase (cumulative — a phase includes all prior phases' menus) */
const PHASE_MENUS: Record<Phase, string[]> = {
  '1-A': [
    '/',
    '/contents/create',
    '/contents',
    '/approvals',
    '/channels',
    '/channels/api-status',
    '/settings/organizations',
    '/users',
    '/approvals/settings',
    '/settings/notifications',
    '/admin',
    '/help',
  ],
  '1-B': [
    '/comments',
    '/comments/dangerous',
    '/comments/reply-templates',
    '/audit-logs',
    '/analytics',
  ],
  '2': [
    '/calendar',
    '/media',
    '/analytics/sentiment',
    '/analytics/prediction',
  ],
  '3': [
    '/reports',
  ],
  '4': [
    '/analytics/benchmark',
  ],
};

/** Returns the set of all menu paths available for the given phase (cumulative). */
function getAvailableMenuPaths(phase: Phase): Set<string> {
  const idx = PHASE_ORDER.indexOf(phase);
  const paths = new Set<string>();
  for (let i = 0; i <= idx; i++) {
    for (const p of PHASE_MENUS[PHASE_ORDER[i]]) {
      paths.add(p);
    }
  }
  return paths;
}

function BadgeLabel({ label, count }: { label: string; count: number }) {
  return (
    <span className="flex items-center justify-between">
      {label}
      {count > 0 && <Badge count={count} size="small" />}
    </span>
  );
}

interface SidebarProps {
  isMobile?: boolean;
}

export default function Sidebar({ isMobile = false }: SidebarProps) {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const mobileMenuOpen = useUiStore((s) => s.mobileMenuOpen);
  const setMobileMenuOpen = useUiStore((s) => s.setMobileMenuOpen);
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

  const isCollapsed = isMobile ? false : collapsed;

  const mainItems: MenuProps['items'] = [
    // ── 대시보드 (독립) ──
    { key: '/', icon: <LayoutDashboard size={18} />, label: '대시보드' },

    // ── 콘텐츠 그룹 ──
    {
      type: 'group',
      label: isCollapsed ? null : '콘텐츠',
      children: [
        { key: '/contents/create', icon: <SquarePen size={18} />, label: '새 콘텐츠 작성' },
        { key: '/contents', icon: <ClipboardList size={18} />, label: '콘텐츠 목록' },
        {
          key: '/approvals',
          icon: <CheckSquare size={18} />,
          label: isCollapsed
            ? '승인 대기'
            : <BadgeLabel label="승인 대기" count={badges?.pending_approvals ?? 0} />,
        },
        { key: '/calendar', icon: <Calendar size={18} />, label: '캘린더' },
      ],
    },

    // ── 댓글 관리 그룹 ──
    {
      type: 'group',
      label: isCollapsed ? null : '댓글 관리',
      children: [
        {
          key: '/comments',
          icon: <MessageSquare size={18} />,
          label: isCollapsed
            ? '통합 댓글함'
            : <BadgeLabel label="통합 댓글함" count={badges?.unread_comments ?? 0} />,
        },
        {
          key: '/comments/dangerous',
          icon: <ShieldAlert size={18} />,
          label: isCollapsed
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
      label: isCollapsed ? null : '분석·리포트',
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
      label: isCollapsed ? null : '채널 관리',
      children: [
        { key: '/channels', icon: <Link2 size={18} />, label: '연동 계정' },
        { key: '/channels/api-status', icon: <Activity size={18} />, label: 'API 상태' },
      ],
    },

    // ── 설정 그룹 ──
    {
      type: 'group',
      label: isCollapsed ? null : '설정',
      children: [
        { key: '/settings/organizations', icon: <Building2 size={18} />, label: '위탁기관 관리' },
        { key: '/users', icon: <Users size={18} />, label: '사용자·권한' },
        { key: '/approvals/settings', icon: <Settings size={18} />, label: '승인 워크플로우 설정' },
        { key: '/settings/notifications', icon: <Bell size={18} />, label: '알림 설정' },
        { key: '/audit-logs', icon: <ScrollText size={18} />, label: '감사 로그' },
      ],
    },

    // ── 시스템 관리 (SA 전용) ──
    { key: '/admin', icon: <Monitor size={18} />, label: '시스템 관리' },
  ];

  const helpItems: MenuProps['items'] = [
    { key: '/help', icon: <CircleHelp size={18} />, label: '도움말', style: { opacity: 0.7 } },
  ];

  // ── RBAC + Phase 필터링 (그룹 내 children 재귀 필터 + 빈 그룹 제거) ──
  const phasePaths = getAvailableMenuPaths(CURRENT_PHASE);

  function isMenuVisible(key: string): boolean {
    const roleAllowed = ROLE_MENUS[key];
    if (!roleAllowed || !userRole || !roleAllowed.includes(userRole)) return false;
    return phasePaths.has(key);
  }

  function filterByRoleAndPhase(items: MenuProps['items']): MenuProps['items'] {
    return items
      ?.map((item) => {
        if (!item) return null;
        if ('type' in item && item.type === 'group') {
          const children = item.children?.filter((child) => {
            if (!child || !('key' in child)) return false;
            return isMenuVisible(child.key as string);
          });
          return children?.length ? { ...item, children } : null;
        }
        if ('key' in item) {
          return isMenuVisible(item.key as string) ? item : null;
        }
        return null;
      })
      .filter(Boolean) as MenuProps['items'];
  }

  const filteredMainItems = filterByRoleAndPhase(mainItems);
  const filteredHelpItems = filterByRoleAndPhase(helpItems);

  // Compute the best matching menu key for the current pathname.
  // For example, /contents/123 should highlight /contents, /contents/123/edit → /contents.
  const ALL_MENU_KEYS = Object.keys(ROLE_MENUS);
  const selectedKey = (() => {
    const path = location.pathname;
    // Exact match first
    if (ALL_MENU_KEYS.includes(path)) return path;
    // Longest prefix match (skip '/' to avoid it always matching)
    let best = '';
    for (const key of ALL_MENU_KEYS) {
      if (key !== '/' && path.startsWith(key) && key.length > best.length) {
        best = key;
      }
    }
    return best || '/';
  })();

  const handleClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key);
    if (isMobile) {
      setMobileMenuOpen(false);
    }
  };

  const menuContent = (
    <nav
      aria-label="메인 네비게이션"
      style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
    >
      <div className="flex h-16 items-center justify-center">
        <PubliSyncLogo collapsed={isCollapsed} size="md" />
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={filteredMainItems}
          onClick={handleClick}
        />
      </div>
      {filteredHelpItems && filteredHelpItems.length > 0 && (
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', padding: '4px 0' }}>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[selectedKey]}
            items={filteredHelpItems}
            onClick={handleClick}
          />
        </div>
      )}
    </nav>
  );

  // -- Mobile: render as Drawer overlay --
  if (isMobile) {
    return (
      <Drawer
        placement="left"
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        width={260}
        styles={{ body: { padding: 0, backgroundColor: '#001529' } }}
        closable={false}
      >
        {menuContent}
      </Drawer>
    );
  }

  // -- Desktop: fixed Sider --
  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={toggleSidebar}
      width={240}
      collapsedWidth={64}
      className="!fixed left-0 top-0 bottom-0 z-10"
      style={{ overflow: 'hidden', height: '100vh' }}
    >
      {menuContent}
    </Sider>
  );
}
