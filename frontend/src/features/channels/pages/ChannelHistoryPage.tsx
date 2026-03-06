import { Select, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';

import { useChannelHistory, useChannels } from '../hooks/useChannels';
import type { ChannelHistoryRecord } from '../types';

const { Title, Text } = Typography;

const PLATFORM_LABELS: Record<string, string> = {
  YOUTUBE: 'YouTube',
  INSTAGRAM: 'Instagram',
  FACEBOOK: 'Facebook',
  X: 'X (Twitter)',
  NAVER_BLOG: '네이버 블로그',
};

const EVENT_LABELS: Record<string, string> = {
  CONNECTED: '채널 연동',
  DISCONNECTED: '연동 해제',
  TOKEN_REFRESHED: '토큰 갱신',
  TOKEN_EXPIRED: '토큰 만료',
  STATUS_CHANGED: '상태 변경',
};

const EVENT_COLORS: Record<string, string> = {
  CONNECTED: 'green',
  DISCONNECTED: 'default',
  TOKEN_REFRESHED: 'blue',
  TOKEN_EXPIRED: 'red',
  STATUS_CHANGED: 'orange',
};

export default function ChannelHistoryPage() {
  const [selectedChannelId, setSelectedChannelId] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const { data: channelsData, isLoading: channelsLoading } = useChannels();
  const { data: historyData, isLoading: historyLoading } = useChannelHistory(
    selectedChannelId,
    page,
  );

  const channelOptions = (channelsData?.data || []).map((ch) => ({
    value: ch.id,
    label: `${PLATFORM_LABELS[ch.platform] || ch.platform} — ${ch.name}`,
  }));

  const selectedChannel = (channelsData?.data || []).find((ch) => ch.id === selectedChannelId);

  const columns: ColumnsType<ChannelHistoryRecord> = [
    {
      title: '일시',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (v: string) => new Date(v).toLocaleString('ko-KR'),
    },
    {
      title: '유형',
      dataIndex: 'event_type',
      key: 'event_type',
      width: 120,
      render: (type: string) => (
        <Tag color={EVENT_COLORS[type] || 'default'}>
          {EVENT_LABELS[type] || type}
        </Tag>
      ),
    },
    {
      title: '채널명',
      key: 'channel_name',
      width: 160,
      render: () =>
        selectedChannel ? (
          <span>
            {PLATFORM_LABELS[selectedChannel.platform] || selectedChannel.platform} — {selectedChannel.name}
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '처리자',
      dataIndex: 'actor_id',
      key: 'actor_id',
      width: 120,
      render: (v: string | null) => v || '-',
    },
    {
      title: '상세',
      dataIndex: 'details',
      key: 'details',
      render: (details: Record<string, unknown> | null) =>
        details ? (
          <Text type="secondary" className="text-xs">
            {JSON.stringify(details)}
          </Text>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <div>
      <Title level={4} className="!mb-4">
        연동 이력
      </Title>

      <div className="mb-4">
        <Select
          placeholder="채널을 선택하세요"
          allowClear
          loading={channelsLoading}
          options={channelOptions}
          value={selectedChannelId}
          onChange={(val) => {
            setSelectedChannelId(val || null);
            setPage(1);
          }}
          style={{ width: 320 }}
        />
      </div>

      <Table
        columns={columns}
        dataSource={selectedChannelId ? historyData?.data || [] : []}
        rowKey="id"
        loading={historyLoading}
        locale={{ emptyText: selectedChannelId ? '이력이 없습니다' : '채널을 선택하세요' }}
        pagination={{
          current: page,
          total: historyData?.meta?.total || 0,
          pageSize: 50,
          onChange: setPage,
          showTotal: (total) => `총 ${total}건`,
        }}
      />
    </div>
  );
}
