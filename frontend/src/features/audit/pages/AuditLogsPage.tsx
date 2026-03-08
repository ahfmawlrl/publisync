import { useState } from 'react';
import { Button, Card, DatePicker, Descriptions, Modal, Select, Space, Spin, Table, Tag, Typography, message } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import { getRoleConfig } from '@/shared/constants/roles';
import type { AuditLogFilters, AuditLogRecord } from '../types';
import { exportAuditLogs, useAuditLogDetail, useAuditLogs } from '../hooks/useAuditLogs';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const ACTION_OPTIONS = [
  { label: '생성', value: 'CREATE' },
  { label: '조회', value: 'READ' },
  { label: '수정', value: 'UPDATE' },
  { label: '삭제', value: 'DELETE' },
  { label: '게시', value: 'PUBLISH' },
  { label: '승인', value: 'APPROVE' },
  { label: '반려', value: 'REJECT' },
  { label: '로그인', value: 'LOGIN' },
  { label: '로그아웃', value: 'LOGOUT' },
  { label: '초대', value: 'INVITE' },
  { label: '내보내기', value: 'EXPORT' },
  { label: '연결', value: 'CONNECT' },
  { label: '해제', value: 'DISCONNECT' },
];

const RESOURCE_TYPE_OPTIONS = [
  { label: '콘텐츠', value: 'content' },
  { label: '채널', value: 'channel' },
  { label: '사용자', value: 'user' },
  { label: '승인', value: 'approval' },
  { label: '기관', value: 'organization' },
  { label: '설정', value: 'settings' },
];

const ACTION_COLORS: Record<string, string> = {
  CREATE: 'green',
  READ: 'default',
  UPDATE: 'blue',
  DELETE: 'red',
  PUBLISH: 'cyan',
  APPROVE: 'green',
  REJECT: 'orange',
  LOGIN: 'geekblue',
  LOGOUT: 'default',
  INVITE: 'purple',
  EXPORT: 'magenta',
  CONNECT: 'lime',
  DISCONNECT: 'volcano',
};

export default function AuditLogsPage() {
  const [filters, setFilters] = useState<AuditLogFilters>({ page: 1, limit: 20 });
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null]);
  const [exporting, setExporting] = useState(false);

  const [detailId, setDetailId] = useState<string | null>(null);

  const { data, isLoading } = useAuditLogs(filters);
  const { data: detailLog, isLoading: isDetailLoading } = useAuditLogDetail(detailId);

  const handleFilterChange = (key: keyof AuditLogFilters, value: string | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }));
  };

  const handleDateChange = (dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setDateRange(dates);
      setFilters((prev) => ({
        ...prev,
        start_date: dates[0]!.startOf('day').toISOString(),
        end_date: dates[1]!.endOf('day').toISOString(),
        page: 1,
      }));
    } else {
      setDateRange([null, null]);
      setFilters((prev) => {
        const next = { ...prev, page: 1 };
        delete next.start_date;
        delete next.end_date;
        return next;
      });
    }
  };

  const handleExport = async () => {
    const startDate = dateRange[0]?.startOf('day').toISOString() ?? dayjs().subtract(30, 'day').toISOString();
    const endDate = dateRange[1]?.endOf('day').toISOString() ?? dayjs().toISOString();
    setExporting(true);
    try {
      await exportAuditLogs({ format: 'csv', start_date: startDate, end_date: endDate });
      message.success('감사 로그가 다운로드됩니다.');
    } catch {
      message.error('내보내기에 실패했습니다.');
    } finally {
      setExporting(false);
    }
  };

  const columns = [
    {
      title: '시간',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '처리자',
      dataIndex: 'actor_name',
      key: 'actor_name',
      width: 100,
      render: (val: string | null) => val || '-',
    },
    {
      title: '역할',
      dataIndex: 'actor_role',
      key: 'actor_role',
      width: 80,
      render: (val: string | null) =>
        val ? <Tag color={getRoleConfig(val).color}>{getRoleConfig(val).short}</Tag> : '-',
    },
    {
      title: '액션',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (val: string) => <Tag color={ACTION_COLORS[val] ?? 'default'}>{val}</Tag>,
    },
    {
      title: '리소스 유형',
      dataIndex: 'resource_type',
      key: 'resource_type',
      width: 120,
    },
    {
      title: '리소스 ID',
      dataIndex: 'resource_id',
      key: 'resource_id',
      width: 280,
      render: (val: string | null) => (val ? <Typography.Text copyable>{val}</Typography.Text> : '-'),
    },
    {
      title: 'IP 주소',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (val: string | null) => val ?? '-',
    },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          감사 로그
        </Title>
        <Button icon={<DownloadOutlined />} loading={exporting} onClick={handleExport}>
          CSV 내보내기
        </Button>
      </div>

      <Card className="mb-4" size="small">
        <Space wrap>
          <Select
            placeholder="액션 필터"
            allowClear
            style={{ width: 160 }}
            options={ACTION_OPTIONS}
            onChange={(val) => handleFilterChange('action', val)}
          />
          <Select
            placeholder="리소스 유형"
            allowClear
            style={{ width: 160 }}
            options={RESOURCE_TYPE_OPTIONS}
            onChange={(val) => handleFilterChange('resource_type', val)}
          />
          <RangePicker value={dateRange} onChange={handleDateChange} />
        </Space>
      </Card>

      <Table<AuditLogRecord>
        rowKey="id"
        columns={columns}
        dataSource={data?.data ?? []}
        loading={isLoading}
        scroll={{ x: 1000 }}
        onRow={(record) => ({
          onClick: () => setDetailId(record.id),
          style: { cursor: 'pointer' },
        })}
        pagination={{
          current: filters.page,
          pageSize: filters.limit,
          total: data?.meta?.total ?? 0,
          showSizeChanger: true,
          showTotal: (total) => `총 ${total}건`,
          onChange: (page, pageSize) => setFilters((prev) => ({ ...prev, page, limit: pageSize })),
        }}
      />

      {/* Detail Modal */}
      <Modal
        title="감사 로그 상세"
        open={!!detailId}
        onCancel={() => setDetailId(null)}
        footer={<Button onClick={() => setDetailId(null)}>닫기</Button>}
        width={640}
      >
        {isDetailLoading ? (
          <div className="flex h-32 items-center justify-center">
            <Spin size="large" />
          </div>
        ) : detailLog ? (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="시간">
              {dayjs(detailLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="액션">
              <Tag color={ACTION_COLORS[detailLog.action] ?? 'default'}>{detailLog.action}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="처리자">
              {(detailLog as AuditLogRecord & { actor_name?: string }).actor_name || detailLog.actor_id || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="역할">
              {detailLog.actor_role ? (
                <Tag color={getRoleConfig(detailLog.actor_role).color}>
                  {getRoleConfig(detailLog.actor_role).label}
                </Tag>
              ) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="리소스 유형">{detailLog.resource_type}</Descriptions.Item>
            <Descriptions.Item label="리소스 ID">
              {detailLog.resource_id ? <Text copyable>{detailLog.resource_id}</Text> : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="IP 주소">{detailLog.ip_address ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="User Agent">
              <Text className="text-xs">{detailLog.user_agent ?? '-'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Request ID">
              {detailLog.request_id ? <Text copyable className="text-xs">{detailLog.request_id}</Text> : '-'}
            </Descriptions.Item>
            {detailLog.changes && Object.keys(detailLog.changes).length > 0 && (
              <Descriptions.Item label="변경 내역">
                <div className="space-y-1">
                  {Object.entries(detailLog.changes).map(([key, value]) => (
                    <div key={key} className="text-xs">
                      <Text type="secondary">{key}: </Text>
                      <Text>{JSON.stringify(value)}</Text>
                    </div>
                  ))}
                </div>
              </Descriptions.Item>
            )}
          </Descriptions>
        ) : (
          <Text type="secondary">로그를 찾을 수 없습니다.</Text>
        )}
      </Modal>
    </div>
  );
}
