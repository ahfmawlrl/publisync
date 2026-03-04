import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons';
import { App, Button, Input, Modal, Select, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';

import { useApproval, useApprovals, useApproveRequest, useRejectRequest } from '../hooks/useApprovals';
import type { ApprovalRequestRecord } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const STATUS_CONFIG: Record<string, { color: string; text: string }> = {
  PENDING_REVIEW: { color: 'orange', text: '검토 대기' },
  IN_REVIEW: { color: 'processing', text: '검토 중' },
  APPROVED: { color: 'green', text: '승인됨' },
  REJECTED: { color: 'red', text: '반려됨' },
};

export default function ApprovalsListPage() {
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [detailId, setDetailId] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState('');
  const [rejectModalId, setRejectModalId] = useState<string | null>(null);

  const { data, isLoading } = useApprovals({ page, status: statusFilter });
  const { data: detailData } = useApproval(detailId);
  const approveMutation = useApproveRequest();
  const rejectMutation = useRejectRequest();

  const handleApprove = (id: string) => {
    approveMutation.mutate(
      { id },
      {
        onSuccess: () => message.success('승인되었습니다'),
        onError: () => message.error('승인에 실패했습니다'),
      },
    );
  };

  const handleReject = () => {
    if (!rejectModalId) return;
    rejectMutation.mutate(
      { id: rejectModalId, comment: rejectComment },
      {
        onSuccess: () => {
          message.success('반려되었습니다');
          setRejectModalId(null);
          setRejectComment('');
        },
        onError: () => message.error('반려에 실패했습니다'),
      },
    );
  };

  const columns: ColumnsType<ApprovalRequestRecord> = [
    {
      title: '콘텐츠 ID',
      dataIndex: 'content_id',
      key: 'content_id',
      ellipsis: true,
      render: (id: string) => <Text copyable={{ text: id }}>{id.slice(0, 8)}...</Text>,
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
      title: '긴급',
      dataIndex: 'is_urgent',
      key: 'is_urgent',
      width: 80,
      render: (v: boolean) => v ? <Tag color="red">긴급</Tag> : '-',
    },
    {
      title: '요청일',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v: string) => new Date(v).toLocaleString('ko-KR'),
    },
    {
      title: '관리',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => setDetailId(record.id)}
            title="상세"
          />
          {['PENDING_REVIEW', 'IN_REVIEW'].includes(record.status) && (
            <>
              <Button
                type="text"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record.id)}
                title="승인"
                style={{ color: '#52c41a' }}
              />
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                onClick={() => setRejectModalId(record.id)}
                title="반려"
                danger
              />
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">승인 관리</Title>
      </div>

      <div className="mb-4">
        <Select
          placeholder="상태 필터"
          allowClear
          style={{ width: 160 }}
          onChange={(v) => { setStatusFilter(v); setPage(1); }}
          options={Object.entries(STATUS_CONFIG).map(([value, { text }]) => ({ value, label: text }))}
        />
      </div>

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

      {/* 승인 상세 모달 */}
      <Modal
        title="승인 상세"
        open={!!detailId}
        onCancel={() => setDetailId(null)}
        footer={null}
        width={600}
      >
        {detailData && (
          <div className="space-y-2">
            <div><Text strong>콘텐츠 ID:</Text> {detailData.content_id}</div>
            <div><Text strong>상태:</Text> {STATUS_CONFIG[detailData.status]?.text || detailData.status}</div>
            <div><Text strong>긴급:</Text> {detailData.is_urgent ? '예' : '아니오'}</div>
            <div><Text strong>요청자:</Text> {detailData.requested_by}</div>
            <div><Text strong>코멘트:</Text> {detailData.comment || '-'}</div>
            <div><Text strong>요청일:</Text> {new Date(detailData.created_at).toLocaleString('ko-KR')}</div>
          </div>
        )}
      </Modal>

      {/* 반려 사유 모달 */}
      <Modal
        title="반려 사유"
        open={!!rejectModalId}
        onCancel={() => { setRejectModalId(null); setRejectComment(''); }}
        onOk={handleReject}
        confirmLoading={rejectMutation.isPending}
        okText="반려"
        cancelText="취소"
      >
        <TextArea
          rows={4}
          value={rejectComment}
          onChange={(e) => setRejectComment(e.target.value)}
          placeholder="반려 사유를 입력하세요"
        />
      </Modal>
    </div>
  );
}
