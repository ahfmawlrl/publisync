import {
  BellOutlined,
  CheckCircleOutlined,
  CheckOutlined,
  CloseCircleOutlined,
  CommentOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  SendOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { App, Badge, Button, Empty, List, Select, Space, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/ko';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { useMarkAllRead, useMarkRead, useNotifications, useUnreadCount } from '../hooks/useNotifications';
import type { NotificationRecord, NotificationType } from '../types';

dayjs.extend(relativeTime);
dayjs.locale('ko');

const { Title, Text, Paragraph } = Typography;

const NOTIFICATION_TYPE_CONFIG: Record<
  NotificationType,
  { icon: React.ReactNode; color: string; label: string }
> = {
  PUBLISH_COMPLETE: {
    icon: <CheckCircleOutlined />,
    color: 'green',
    label: '게시 완료',
  },
  PUBLISH_FAILED: {
    icon: <CloseCircleOutlined />,
    color: 'red',
    label: '게시 실패',
  },
  APPROVAL_REQUEST: {
    icon: <SendOutlined />,
    color: 'orange',
    label: '승인 요청',
  },
  APPROVAL_RESULT: {
    icon: <CheckOutlined />,
    color: 'cyan',
    label: '승인 결과',
  },
  DANGEROUS_COMMENT: {
    icon: <ExclamationCircleOutlined />,
    color: 'red',
    label: '위험 댓글',
  },
  COMMENT_NEW: {
    icon: <CommentOutlined />,
    color: 'blue',
    label: '새 댓글',
  },
  TOKEN_EXPIRING: {
    icon: <WarningOutlined />,
    color: 'warning',
    label: '토큰 만료',
  },
  SYSTEM: {
    icon: <InfoCircleOutlined />,
    color: 'default',
    label: '시스템',
  },
};

const TYPE_OPTIONS = Object.entries(NOTIFICATION_TYPE_CONFIG).map(([value, { label }]) => ({
  value,
  label,
}));

export default function NotificationsPage() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<string | undefined>();

  const { data, isLoading } = useNotifications({
    page,
    limit: 20,
    type: typeFilter,
  });
  const { data: unreadData } = useUnreadCount();

  const markReadMutation = useMarkRead();
  const markAllReadMutation = useMarkAllRead();

  const handleMarkRead = (notification: NotificationRecord) => {
    if (notification.is_read) return;
    markReadMutation.mutate(notification.id, {
      onError: () => message.error('알림 읽음 처리에 실패했습니다'),
    });
  };

  const handleMarkAllRead = () => {
    markAllReadMutation.mutate(undefined, {
      onSuccess: (data) => {
        message.success(`${data?.affected ?? 0}개 알림을 읽음 처리했습니다`);
      },
      onError: () => message.error('일괄 읽음 처리에 실패했습니다'),
    });
  };

  const handleNotificationClick = (notification: NotificationRecord) => {
    handleMarkRead(notification);
    if (notification.action_url) {
      navigate(notification.action_url);
    }
  };

  const renderNotificationItem = (item: NotificationRecord) => {
    const config = NOTIFICATION_TYPE_CONFIG[item.type] || NOTIFICATION_TYPE_CONFIG.SYSTEM;

    return (
      <List.Item
        key={item.id}
        className={`cursor-pointer transition-colors hover:bg-gray-50 ${
          !item.is_read ? 'bg-blue-50/50' : ''
        }`}
        onClick={() => handleNotificationClick(item)}
        style={{ padding: '12px 16px' }}
      >
        <List.Item.Meta
          avatar={
            <Badge dot={!item.is_read}>
              <span
                className="flex h-10 w-10 items-center justify-center rounded-full text-lg"
                style={{
                  backgroundColor: `var(--ant-color-${config.color === 'default' ? 'text-quaternary' : config.color}-bg, #f5f5f5)`,
                  color: `var(--ant-color-${config.color === 'default' ? 'text-secondary' : config.color}, #888)`,
                }}
              >
                {config.icon}
              </span>
            </Badge>
          }
          title={
            <Space size={8}>
              <Text strong={!item.is_read}>{item.title}</Text>
              <Tag color={config.color}>{config.label}</Tag>
            </Space>
          }
          description={
            <div>
              <Paragraph
                className="!mb-1"
                type="secondary"
                ellipsis={{ rows: 2 }}
              >
                {item.message}
              </Paragraph>
              <Text type="secondary" className="text-xs">
                {dayjs(item.created_at).fromNow()}
              </Text>
            </div>
          }
        />
      </List.Item>
    );
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Space>
          <Title level={4} className="!mb-0">
            <BellOutlined className="mr-2" />
            알림 센터
          </Title>
          {unreadData && unreadData.count > 0 && (
            <Badge count={unreadData.count} style={{ marginTop: -4 }} />
          )}
        </Space>
        <Button
          onClick={handleMarkAllRead}
          loading={markAllReadMutation.isPending}
          disabled={!unreadData || unreadData.count === 0}
          icon={<CheckOutlined />}
        >
          모두 읽음 처리
        </Button>
      </div>

      <div className="mb-4">
        <Select
          placeholder="알림 유형 필터"
          allowClear
          style={{ width: 180 }}
          onChange={(v) => {
            setTypeFilter(v);
            setPage(1);
          }}
          options={TYPE_OPTIONS}
        />
      </div>

      <List
        loading={isLoading}
        dataSource={data?.data || []}
        renderItem={renderNotificationItem}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="알림이 없습니다"
            />
          ),
        }}
        pagination={{
          current: page,
          total: data?.meta?.total || 0,
          pageSize: 20,
          onChange: setPage,
          showTotal: (total) => `총 ${total}개`,
        }}
      />
    </div>
  );
}
