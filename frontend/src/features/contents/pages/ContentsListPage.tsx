import { DeleteOutlined, EditOutlined, EyeOutlined, PlusOutlined, SendOutlined } from '@ant-design/icons';
import { App, Button, Input, Popconfirm, Select, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { useBulkAction, useContents, useDeleteContent, useRequestReview } from '../hooks/useContents';
import type { ContentRecord } from '../types';

const { Title } = Typography;
const { Search } = Input;

const STATUS_CONFIG: Record<string, { color: string; text: string }> = {
  DRAFT: { color: 'default', text: '초안' },
  PENDING_REVIEW: { color: 'orange', text: '검토 대기' },
  IN_REVIEW: { color: 'processing', text: '검토 중' },
  APPROVED: { color: 'cyan', text: '승인됨' },
  REJECTED: { color: 'red', text: '반려됨' },
  SCHEDULED: { color: 'blue', text: '예약됨' },
  PUBLISHING: { color: 'processing', text: '게시 중' },
  PUBLISHED: { color: 'green', text: '게시 완료' },
  PARTIALLY_PUBLISHED: { color: 'warning', text: '부분 게시' },
  PUBLISH_FAILED: { color: 'error', text: '게시 실패' },
  CANCELLED: { color: 'default', text: '취소됨' },
  ARCHIVED: { color: 'default', text: '보관됨' },
};

const PLATFORM_COLORS: Record<string, string> = {
  YOUTUBE: 'red',
  INSTAGRAM: 'purple',
  FACEBOOK: 'blue',
  X: 'default',
  NAVER_BLOG: 'green',
};

export default function ContentsListPage() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [platformFilter, setPlatformFilter] = useState<string | undefined>();
  const [searchText, setSearchText] = useState<string | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const { data, isLoading } = useContents({
    page,
    status: statusFilter,
    platform: platformFilter,
    search: searchText,
  });

  const deleteMutation = useDeleteContent();
  const reviewMutation = useRequestReview();
  const bulkMutation = useBulkAction();

  const handleBulkDelete = () => {
    bulkMutation.mutate(
      { content_ids: selectedRowKeys as string[], action: 'delete' },
      {
        onSuccess: (data) => {
          message.success(`${data?.affected ?? 0}개 콘텐츠가 삭제되었습니다`);
          setSelectedRowKeys([]);
        },
        onError: () => message.error('일괄 삭제에 실패했습니다'),
      },
    );
  };

  const columns: ColumnsType<ContentRecord> = [
    {
      title: '제목',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title: string, record) => (
        <a onClick={() => navigate(`/contents/${record.id}`)}>{title}</a>
      ),
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (s: string) => {
        const cfg = STATUS_CONFIG[s] || { color: 'default', text: s };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '플랫폼',
      dataIndex: 'platforms',
      key: 'platforms',
      width: 200,
      render: (platforms: string[]) => (
        <Space size={2} wrap>
          {platforms.map((p) => (
            <Tag key={p} color={PLATFORM_COLORS[p]}>{p}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '예약일시',
      dataIndex: 'scheduled_at',
      key: 'scheduled_at',
      width: 160,
      render: (v: string | null) => (v ? new Date(v).toLocaleString('ko-KR') : '-'),
    },
    {
      title: '작성일',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v: string) => new Date(v).toLocaleString('ko-KR'),
    },
    {
      title: '관리',
      key: 'actions',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/contents/${record.id}`)}
            title="상세"
          />
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/contents/${record.id}/edit`)}
            title="수정"
            disabled={!['DRAFT', 'REJECTED'].includes(record.status)}
          />
          {record.status === 'DRAFT' && (
            <Button
              type="text"
              size="small"
              icon={<SendOutlined />}
              onClick={() => {
                reviewMutation.mutate(record.id, {
                  onSuccess: () => message.success('검토 요청이 완료되었습니다'),
                  onError: () => message.error('검토 요청에 실패했습니다'),
                });
              }}
              title="검토 요청"
            />
          )}
          <Popconfirm
            title="콘텐츠를 삭제하시겠습니까?"
            onConfirm={() => {
              deleteMutation.mutate(record.id, {
                onSuccess: () => message.success('콘텐츠가 삭제되었습니다'),
                onError: () => message.error('콘텐츠 삭제에 실패했습니다'),
              });
            }}
            okText="삭제"
            cancelText="취소"
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} title="삭제" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">콘텐츠 관리</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/contents/create')}>
          콘텐츠 작성
        </Button>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <Select
          placeholder="상태 필터"
          allowClear
          style={{ width: 140 }}
          onChange={(v) => { setStatusFilter(v); setPage(1); }}
          options={Object.entries(STATUS_CONFIG).map(([value, { text }]) => ({ value, label: text }))}
        />
        <Select
          placeholder="플랫폼"
          allowClear
          style={{ width: 140 }}
          onChange={(v) => { setPlatformFilter(v); setPage(1); }}
          options={[
            { value: 'YOUTUBE', label: 'YouTube' },
            { value: 'INSTAGRAM', label: 'Instagram' },
            { value: 'FACEBOOK', label: 'Facebook' },
            { value: 'X', label: 'X' },
            { value: 'NAVER_BLOG', label: '네이버 블로그' },
          ]}
        />
        <Search
          placeholder="제목 검색"
          allowClear
          style={{ width: 240 }}
          onSearch={(v) => { setSearchText(v || undefined); setPage(1); }}
        />
        {selectedRowKeys.length > 0 && (
          <Popconfirm title={`${selectedRowKeys.length}개 항목을 삭제하시겠습니까?`} onConfirm={handleBulkDelete} okText="삭제" cancelText="취소">
            <Button danger>일괄 삭제 ({selectedRowKeys.length})</Button>
          </Popconfirm>
        )}
      </div>

      <Table
        columns={columns}
        dataSource={data?.data || []}
        rowKey="id"
        loading={isLoading}
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
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
