import { useState } from 'react';
import { Button, Card, DatePicker, Select, Space, Table, Tag, Typography, message } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import type { AuditLogFilters, AuditLogRecord } from '../types';
import { exportAuditLogs, useAuditLogs } from '../hooks/useAuditLogs';

const { Title } = Typography;
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

const ROLE_LABELS: Record<string, string> = {
  SYSTEM_ADMIN: 'SA',
  AGENCY_MANAGER: 'AM',
  AGENCY_OPERATOR: 'AO',
  CLIENT_DIRECTOR: 'CD',
};

const ROLE_COLORS: Record<string, string> = {
  SYSTEM_ADMIN: 'red',
  AGENCY_MANAGER: 'blue',
  AGENCY_OPERATOR: 'green',
  CLIENT_DIRECTOR: 'orange',
};

export default function AuditLogsPage() {
  const [filters, setFilters] = useState<AuditLogFilters>({ page: 1, limit: 20 });
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null]);
  const [exporting, setExporting] = useState(false);

  const { data, isLoading } = useAuditLogs(filters);

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
      title: '역할',
      dataIndex: 'actor_role',
      key: 'actor_role',
      width: 80,
      render: (val: string | null) =>
        val ? <Tag color={ROLE_COLORS[val] ?? 'default'}>{ROLE_LABELS[val] ?? val}</Tag> : '-',
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
        pagination={{
          current: filters.page,
          pageSize: filters.limit,
          total: data?.meta?.total ?? 0,
          showSizeChanger: true,
          showTotal: (total) => `총 ${total}건`,
          onChange: (page, pageSize) => setFilters((prev) => ({ ...prev, page, limit: pageSize })),
        }}
      />
    </div>
  );
}
