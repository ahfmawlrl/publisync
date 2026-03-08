import { DeleteOutlined, HistoryOutlined, ReloadOutlined } from '@ant-design/icons';
import { App, Button, Card, Drawer, Modal, Popconfirm, Progress, Select, Space, Table, Tabs, Tag, Timeline, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';

import {
  useApiStatus,
  useChannelHistory,
  useChannels,
  useConnectChannel,
  useDisconnectChannel,
  useRefreshChannelToken,
} from '../hooks/useChannels';
import type { ChannelRecord } from '../types';

const { Title, Text } = Typography;

const PLATFORM_LABELS: Record<string, string> = {
  YOUTUBE: 'YouTube',
  INSTAGRAM: 'Instagram',
  FACEBOOK: 'Facebook',
  X: 'X (Twitter)',
  NAVER_BLOG: '네이버 블로그',
};

const PLATFORM_COLORS: Record<string, string> = {
  YOUTUBE: 'red',
  INSTAGRAM: 'purple',
  FACEBOOK: 'blue',
  X: 'default',
  NAVER_BLOG: 'green',
};

const STATUS_CONFIG: Record<string, { color: string; text: string }> = {
  ACTIVE: { color: 'green', text: '연동됨' },
  EXPIRING: { color: 'orange', text: '만료 임박' },
  EXPIRED: { color: 'red', text: '만료됨' },
  DISCONNECTED: { color: 'default', text: '미연동' },
};

const EVENT_LABELS: Record<string, string> = {
  CONNECTED: '채널 연동',
  DISCONNECTED: '연동 해제',
  TOKEN_REFRESHED: '토큰 갱신',
  TOKEN_EXPIRED: '토큰 만료',
  STATUS_CHANGED: '상태 변경',
};

export default function ChannelsPage() {
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [connectOpen, setConnectOpen] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<string>('YOUTUBE');
  const [historyChannelId, setHistoryChannelId] = useState<string | null>(null);

  const { data, isLoading } = useChannels(page);
  const { data: apiStatus } = useApiStatus();
  const { data: historyData } = useChannelHistory(historyChannelId);
  const { initiate } = useConnectChannel();
  const disconnectMutation = useDisconnectChannel();
  const refreshMutation = useRefreshChannelToken();

  const handleConnect = async () => {
    try {
      const result = await initiate.mutateAsync({
        platform: selectedPlatform,
        redirect_uri: `${window.location.origin}/channels/callback`,
      });
      window.open(result.auth_url, '_blank', 'width=600,height=700');
      setConnectOpen(false);
      message.info('OAuth 인증 창이 열렸습니다. 인증을 완료하세요.');
    } catch {
      message.error('채널 연동 시작에 실패했습니다');
    }
  };

  const columns: ColumnsType<ChannelRecord> = [
    {
      title: '플랫폼',
      dataIndex: 'platform',
      key: 'platform',
      render: (p: string) => <Tag color={PLATFORM_COLORS[p]}>{PLATFORM_LABELS[p] || p}</Tag>,
    },
    { title: '채널명', dataIndex: 'name', key: 'name' },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => {
        const cfg = STATUS_CONFIG[s] || { color: 'default', text: s };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '토큰 만료',
      dataIndex: 'token_expires_at',
      key: 'token_expires_at',
      render: (v: string | null) => (v ? new Date(v).toLocaleString('ko-KR') : '-'),
    },
    {
      title: '관리',
      key: 'actions',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => {
              refreshMutation.mutate(record.id, {
                onSuccess: () => message.success('토큰이 갱신되었습니다'),
                onError: () => message.error('토큰 갱신에 실패했습니다'),
              });
            }}
            title="토큰 갱신"
          />
          <Button
            type="text"
            size="small"
            icon={<HistoryOutlined />}
            onClick={() => setHistoryChannelId(record.id)}
            title="이력"
          />
          <Popconfirm
            title="채널 연동을 해제하시겠습니까?"
            onConfirm={() => {
              disconnectMutation.mutate(record.id, {
                onSuccess: () => message.success('채널이 해제되었습니다'),
                onError: () => message.error('채널 해제에 실패했습니다'),
              });
            }}
            okText="해제"
            cancelText="취소"
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} title="연동 해제" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">채널 관리</Title>
        <Button type="primary" onClick={() => setConnectOpen(true)}>채널 연동</Button>
      </div>

      <Tabs
        defaultActiveKey="channels"
        items={[
          {
            key: 'channels',
            label: '연동 계정',
            children: (
              <Table
                columns={columns}
                dataSource={data?.data || []}
                rowKey="id"
                loading={isLoading}
                pagination={{
                  current: page,
                  total: data?.meta?.total || 0,
                  pageSize: 20,
                  onChange: setPage,
                  showTotal: (total) => `총 ${total}개`,
                }}
              />
            ),
          },
          {
            key: 'api-status',
            label: 'API 상태',
            children: apiStatus && apiStatus.length > 0 ? (
              <Card title="API 사용 현황">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {apiStatus.map((s) => (
                    <div key={s.platform}>
                      <Text strong>{PLATFORM_LABELS[s.platform] || s.platform}</Text>
                      <Progress
                        percent={s.percentage_used}
                        status={s.percentage_used > 90 ? 'exception' : s.percentage_used > 70 ? 'active' : 'normal'}
                        size="small"
                      />
                      <Text type="secondary" className="text-xs">
                        {s.requests_used} / {s.requests_limit} ({s.window})
                      </Text>
                    </div>
                  ))}
                </div>
              </Card>
            ) : (
              <Card>
                <Text type="secondary">API 상태 데이터가 없습니다</Text>
              </Card>
            ),
          },
        ]}
      />

      {/* 연동 모달 */}
      <Modal
        title="채널 연동"
        open={connectOpen}
        onCancel={() => setConnectOpen(false)}
        onOk={handleConnect}
        confirmLoading={initiate.isPending}
        okText="연동 시작"
        cancelText="취소"
      >
        <Select
          value={selectedPlatform}
          onChange={setSelectedPlatform}
          style={{ width: '100%' }}
          options={Object.entries(PLATFORM_LABELS).map(([value, label]) => ({ value, label }))}
        />
      </Modal>

      {/* 이력 Drawer */}
      <Drawer
        title="연동 이력"
        open={!!historyChannelId}
        onClose={() => setHistoryChannelId(null)}
        width={400}
      >
        <Timeline
          items={(historyData?.data || []).map((h) => ({
            children: (
              <div>
                <Text strong>{EVENT_LABELS[h.event_type] || h.event_type}</Text>
                <br />
                <Text type="secondary" className="text-xs">
                  {new Date(h.created_at).toLocaleString('ko-KR')}
                </Text>
              </div>
            ),
          }))}
        />
      </Drawer>
    </div>
  );
}
