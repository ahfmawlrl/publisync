import {
  AlertOutlined,
  BellOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CommentOutlined,
  SettingOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Badge, Button, Drawer, Empty, List, Space, Spin, Tabs, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router';

import { useWorkspaceStore } from '@/shared/stores/useWorkspaceStore';

import { useMarkAllRead, useMarkRead, useNotifications, useUnreadCount } from '../hooks/useNotifications';
import type { NotificationRecord, NotificationType } from '../types';

const { Text } = Typography;

interface NotificationDrawerProps {
  open: boolean;
  onClose: () => void;
}

const TYPE_CONFIG: Record<NotificationType, { icon: React.ReactNode; color: string; label: string }> = {
  DANGEROUS_COMMENT: { icon: <AlertOutlined />, color: '#ff4d4f', label: '위험 댓글' },
  APPROVAL_REQUEST: { icon: <BellOutlined />, color: '#faad14', label: '승인 요청' },
  APPROVAL_RESULT: { icon: <CheckCircleOutlined />, color: '#52c41a', label: '승인 결과' },
  PUBLISH_COMPLETE: { icon: <CheckCircleOutlined />, color: '#52c41a', label: '게시 완료' },
  PUBLISH_FAILED: { icon: <CloseCircleOutlined />, color: '#ff4d4f', label: '게시 실패' },
  TOKEN_EXPIRING: { icon: <WarningOutlined />, color: '#faad14', label: '토큰 만료' },
  COMMENT_NEW: { icon: <CommentOutlined />, color: '#1677ff', label: '새 댓글' },
  SYSTEM: { icon: <BellOutlined />, color: '#8c8c8c', label: '시스템' },
};

const ACTION_MAP: Partial<Record<NotificationType, { label: string; path: string }>> = {
  DANGEROUS_COMMENT: { label: '대응하기', path: '/comments/dangerous' },
  APPROVAL_REQUEST: { label: '검수하기', path: '/approvals' },
  APPROVAL_RESULT: { label: '확인하기', path: '/approvals' },
  PUBLISH_COMPLETE: { label: '확인하기', path: '/contents' },
  PUBLISH_FAILED: { label: '확인하기', path: '/contents' },
  COMMENT_NEW: { label: '확인하기', path: '/comments' },
  TOKEN_EXPIRING: { label: '갱신하기', path: '/channels' },
};

function formatRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return '방금 전';
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}시간 전`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}일 전`;
  return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
}

function groupByDate(items: NotificationRecord[]): { label: string; items: NotificationRecord[] }[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const groups: Record<string, NotificationRecord[]> = {};
  for (const item of items) {
    const date = new Date(item.created_at);
    date.setHours(0, 0, 0, 0);
    let label: string;
    if (date.getTime() === today.getTime()) label = '오늘';
    else if (date.getTime() === yesterday.getTime()) label = '어제';
    else label = date.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
    if (!groups[label]) groups[label] = [];
    groups[label].push(item);
  }
  return Object.entries(groups).map(([label, items]) => ({ label, items }));
}

export default function NotificationDrawer({ open, onClose }: NotificationDrawerProps) {
  const navigate = useNavigate();
  const currentOrgId = useWorkspaceStore((s) => s.currentOrgId);
  const hasValidWorkspace = !!currentOrgId && currentOrgId !== 'all';
  const { data: unread } = useUnreadCount(hasValidWorkspace);
  const markReadMutation = useMarkRead();
  const markAllReadMutation = useMarkAllRead();

  const { data: allData, isLoading: allLoading } = useNotifications({ page: 1, limit: 50 }, hasValidWorkspace);
  const allItems = allData?.data || [];
  const unreadItems = allItems.filter((n) => !n.is_read);

  const handleAction = (notification: NotificationRecord) => {
    if (!notification.is_read) markReadMutation.mutate(notification.id);
    if (notification.action_url) {
      navigate(notification.action_url);
    } else {
      const action = ACTION_MAP[notification.type];
      if (action) navigate(action.path);
    }
    onClose();
  };

  const handleMarkAllRead = () => {
    markAllReadMutation.mutate();
  };

  const renderItem = (item: NotificationRecord) => {
    const cfg = TYPE_CONFIG[item.type] || TYPE_CONFIG.SYSTEM;
    const action = ACTION_MAP[item.type];
    return (
      <List.Item
        key={item.id}
        className={`cursor-pointer transition-colors hover:bg-gray-50 ${!item.is_read ? 'bg-blue-50/50' : ''}`}
        onClick={() => {
          if (!item.is_read) markReadMutation.mutate(item.id);
        }}
      >
        <div className="flex w-full items-start gap-3">
          <div
            className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full"
            style={{ backgroundColor: `${cfg.color}15`, color: cfg.color }}
          >
            {cfg.icon}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Tag color={cfg.color} className="!text-xs">{cfg.label}</Tag>
              {!item.is_read && <Badge status="processing" />}
            </div>
            <Text strong className="block text-sm">{item.title}</Text>
            <Text type="secondary" className="block text-xs" ellipsis>{item.message}</Text>
            <div className="mt-1 flex items-center justify-between">
              <Text type="secondary" className="text-xs">{formatRelativeTime(item.created_at)}</Text>
              {action && (
                <Button
                  type="link"
                  size="small"
                  className="!p-0 !text-xs"
                  onClick={(e) => { e.stopPropagation(); handleAction(item); }}
                >
                  {action.label}
                </Button>
              )}
            </div>
          </div>
        </div>
      </List.Item>
    );
  };

  const renderList = (items: NotificationRecord[], loading: boolean) => {
    if (loading) return <div className="flex justify-center py-8"><Spin /></div>;
    if (!items.length) return <Empty description="알림이 없습니다" />;
    const groups = groupByDate(items);
    return (
      <div>
        {groups.map((group) => (
          <div key={group.label}>
            <div className="px-4 py-2">
              <Text type="secondary" className="text-xs font-medium uppercase">{group.label}</Text>
            </div>
            <List
              size="small"
              split={false}
              dataSource={group.items}
              renderItem={renderItem}
            />
          </div>
        ))}
      </div>
    );
  };

  return (
    <Drawer
      title={
        <div className="flex items-center justify-between">
          <span>알림 센터</span>
          <Space>
            <Button
              type="text"
              size="small"
              icon={<SettingOutlined />}
              onClick={() => { navigate('/settings/notifications'); onClose(); }}
            />
          </Space>
        </div>
      }
      placement="right"
      width={380}
      open={open}
      onClose={onClose}
      styles={{ body: { padding: 0 } }}
      extra={
        unreadItems.length > 0 ? (
          <Button type="link" size="small" onClick={handleMarkAllRead} loading={markAllReadMutation.isPending}>
            전체 읽음
          </Button>
        ) : null
      }
    >
      <Tabs
        defaultActiveKey="all"
        className="px-4"
        items={[
          {
            key: 'all',
            label: '전체',
            children: renderList(allItems, allLoading),
          },
          {
            key: 'unread',
            label: (
              <Badge count={unread?.count ?? 0} size="small" offset={[8, 0]}>
                미읽음
              </Badge>
            ),
            children: renderList(unreadItems, allLoading),
          },
        ]}
      />
    </Drawer>
  );
}
