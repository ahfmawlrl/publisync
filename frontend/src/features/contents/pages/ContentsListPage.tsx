import { DeleteOutlined, EditOutlined, EyeOutlined, PlusOutlined, SendOutlined } from '@ant-design/icons';
import { App, Button, Input, Popconfirm, Select, Space, Table, Tabs, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { getStatusConfig } from '@/shared/constants/contentStatus';
import { CONTENT_MESSAGES } from '@/shared/constants/messages';
import { getPlatformConfig } from '@/shared/constants/platform';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useBulkAction, useContents, useDeleteContent, useRequestReview } from '../hooks/useContents';
import type { ContentRecord } from '../types';

const { Title } = Typography;
const { Search } = Input;

type StatusTab = 'all' | 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'PUBLISHED' | 'REJECTED';

export default function ContentsListPage() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const userRole = useAuthStore((s) => s.user?.role);
  const canCreate = userRole !== 'CLIENT_DIRECTOR';
  const [page, setPage] = useState(1);
  const [statusTab, setStatusTab] = useState<StatusTab>('all');
  const [platformFilter, setPlatformFilter] = useState<string | undefined>();
  const [searchText, setSearchText] = useState<string | undefined>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const { data, isLoading } = useContents({
    page,
    status: statusTab === 'all' ? undefined : statusTab,
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
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (s: string) => {
        const cfg = getStatusConfig(s);
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
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
      title: '플랫폼',
      dataIndex: 'platforms',
      key: 'platforms',
      width: 160,
      render: (platforms: string[]) => (
        <span>
          {platforms.map((p) => getPlatformConfig(p).short).join('·')}
        </span>
      ),
    },
    {
      title: '작성자',
      dataIndex: 'author_name',
      key: 'author_name',
      width: 100,
      render: (name: string | undefined) => name || '-',
    },
    {
      title: '날짜',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 100,
      render: (v: string) => new Date(v).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }),
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
            <Popconfirm
              title="검토를 요청하시겠습니까?"
              onConfirm={() => {
                reviewMutation.mutate(record.id, {
                  onSuccess: () => message.success(CONTENT_MESSAGES.REQUEST_REVIEW_SUCCESS),
                  onError: () => message.error(CONTENT_MESSAGES.REQUEST_REVIEW_ERROR),
                });
              }}
              okText="요청"
              cancelText="취소"
            >
              <Button
                type="text"
                size="small"
                icon={<SendOutlined />}
                title="검토 요청"
              />
            </Popconfirm>
          )}
          <Popconfirm
            title={CONTENT_MESSAGES.DELETE_CONFIRM}
            onConfirm={() => {
              deleteMutation.mutate(record.id, {
                onSuccess: () => message.success(CONTENT_MESSAGES.DELETE_SUCCESS),
                onError: () => message.error(CONTENT_MESSAGES.DELETE_ERROR),
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
        <Title level={4} className="!mb-0">콘텐츠 목록</Title>
        {canCreate && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/contents/create')}>
            + 새 콘텐츠
          </Button>
        )}
      </div>

      <Tabs
        activeKey={statusTab}
        onChange={(key) => { setStatusTab(key as StatusTab); setPage(1); }}
        items={[
          { key: 'all', label: '전체' },
          { key: 'DRAFT', label: '작성 중' },
          { key: 'PENDING_REVIEW', label: '검토 대기' },
          { key: 'APPROVED', label: '승인됨' },
          { key: 'PUBLISHED', label: '게시 완료' },
          { key: 'REJECTED', label: '반려됨' },
        ]}
      />

      <div className="mb-4 flex items-center gap-3">
        <Select
          placeholder="전체 플랫폼"
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
        <Select
          placeholder="최근 30일"
          style={{ width: 120 }}
          defaultValue="30d"
          options={[
            { value: '7d', label: '최근 7일' },
            { value: '30d', label: '최근 30일' },
            { value: '90d', label: '최근 90일' },
          ]}
        />
        <Search
          placeholder="검색..."
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
          showTotal: (total) => `총 ${total}건${selectedRowKeys.length > 0 ? ` | 선택: ${selectedRowKeys.length}건` : ''}`,
        }}
      />
    </div>
  );
}
