import { ArrowLeftOutlined } from '@ant-design/icons';
import { App, Button, Card, Empty, Input, Modal, Spin, Tabs, Tag, Typography } from 'antd';
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

const PLATFORM_COLORS: Record<string, string> = {
  YOUTUBE: 'red',
  INSTAGRAM: 'purple',
  FACEBOOK: 'blue',
  X: 'default',
  NAVER_BLOG: 'green',
};

const PLATFORM_LABELS: Record<string, string> = {
  YOUTUBE: 'YouTube',
  INSTAGRAM: 'Instagram',
  FACEBOOK: 'Facebook',
  X: 'X',
  NAVER_BLOG: '블로그',
};

type TabKey = 'mine' | 'requested' | 'all';

export default function ApprovalsListPage() {
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState<TabKey>('mine');
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState('');
  const [rejectModalId, setRejectModalId] = useState<string | null>(null);

  const statusFilter = activeTab === 'mine' ? 'PENDING_REVIEW' : activeTab === 'requested' ? undefined : undefined;
  const { data, isLoading } = useApprovals({ page, status: statusFilter });
  const { data: detailData, isLoading: detailLoading } = useApproval(reviewId);
  const approveMutation = useApproveRequest();
  const rejectMutation = useRejectRequest();

  const handleApprove = (id: string) => {
    approveMutation.mutate(
      { id },
      {
        onSuccess: () => {
          message.success('승인되었습니다');
          setReviewId(null);
        },
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
          setReviewId(null);
        },
        onError: () => message.error('반려에 실패했습니다'),
      },
    );
  };

  const items = data?.data || [];
  const pendingCount = items.filter((i) => ['PENDING_REVIEW', 'IN_REVIEW'].includes(i.status)).length;

  const renderApprovalCard = (record: ApprovalRequestRecord) => {
    const isUrgent = record.is_urgent;
    return (
      <div
        key={record.id}
        className="mb-3 cursor-pointer rounded-lg border-l-4 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
        style={{
          borderLeftColor: isUrgent ? '#ff4d4f' : '#faad14',
        }}
        onClick={() => setReviewId(record.id)}
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <Tag color={isUrgent ? 'red' : 'gold'}>{isUrgent ? '긴급' : '일반'}</Tag>
          <Text strong>{record.content_title || record.content_id.slice(0, 8)}</Text>
          <Tag color={STATUS_CONFIG[record.status]?.color}>
            {STATUS_CONFIG[record.status]?.text || record.status}
          </Tag>
          {record.platforms && record.platforms.length > 0 && (
            <>
              {record.platforms.map((p) => (
                <Tag key={p} color={PLATFORM_COLORS[p]} className="text-xs">
                  {PLATFORM_LABELS[p] || p}
                </Tag>
              ))}
            </>
          )}
        </div>
        <div className="text-xs text-gray-500">
          요청자: {record.requested_by} · 요청일: {new Date(record.created_at).toLocaleString('ko-KR')}
        </div>
        {record.comment && (
          <div className="mt-1 text-xs text-gray-500">메모: &quot;{record.comment}&quot;</div>
        )}
        <div className="mt-2 text-right">
          {['PENDING_REVIEW', 'IN_REVIEW'].includes(record.status) && (
            <Button type="primary" size="small" onClick={(e) => { e.stopPropagation(); setReviewId(record.id); }}>
              검수하기
            </Button>
          )}
        </div>
      </div>
    );
  };

  // Review detail (split panel)
  if (reviewId) {
    return (
      <div>
        <div className="mb-4">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => setReviewId(null)}>
            목록으로
          </Button>
        </div>
        <Title level={4} className="!mb-4">
          콘텐츠 검수
        </Title>

        {detailLoading ? (
          <div className="flex h-64 items-center justify-center"><Spin size="large" /></div>
        ) : detailData ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Left: Content preview */}
            <Card title="콘텐츠 내용">
              <div className="mb-3 flex h-44 items-center justify-center rounded bg-gray-100 text-gray-400">
                미디어 미리보기
              </div>
              <div className="text-sm">
                <div className="mb-1"><Text strong>콘텐츠 ID:</Text> {detailData.content_id}</div>
                <div className="mb-1"><Text strong>상태:</Text> {STATUS_CONFIG[detailData.status]?.text || detailData.status}</div>
                <div className="mb-1"><Text strong>긴급:</Text> {detailData.is_urgent ? '예' : '아니오'}</div>
              </div>
            </Card>

            {/* Right: Review panel */}
            <div className="space-y-4">
              <Card title="AI 검수 결과" size="small">
                <div className="text-sm">
                  <div className="py-1">✅ 표현 적합성: 통과</div>
                  <div className="py-1">✅ 개인정보: 미검출</div>
                  <div className="py-1">⚠️ 이미지 대체텍스트 미입력 1건</div>
                </div>
              </Card>

              <Card title="승인 이력" size="small">
                <div className="text-sm">
                  <div className="py-1">{new Date(detailData.created_at).toLocaleDateString('ko-KR')} 검토 요청 ({detailData.requested_by})</div>
                  {detailData.comment && (
                    <div className="py-1">코멘트: {detailData.comment}</div>
                  )}
                </div>
              </Card>

              <Card title="검수 의견" size="small">
                <TextArea
                  rows={3}
                  placeholder="의견 입력..."
                  value={rejectComment}
                  onChange={(e) => setRejectComment(e.target.value)}
                />
                <div className="mt-3 flex justify-end gap-2">
                  <Button
                    danger
                    onClick={() => setRejectModalId(reviewId)}
                  >
                    반려
                  </Button>
                  <Button
                    type="primary"
                    style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
                    onClick={() => handleApprove(reviewId)}
                    loading={approveMutation.isPending}
                  >
                    승인 후 게시
                  </Button>
                </div>
              </Card>
            </div>
          </div>
        ) : (
          <Empty description="데이터를 불러올 수 없습니다" />
        )}

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

  // List view
  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">승인 대기</Title>
        {pendingCount > 0 && (
          <Text style={{ color: '#ff4d4f', fontWeight: 600 }}>{pendingCount}건 대기</Text>
        )}
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={(key) => { setActiveTab(key as TabKey); setPage(1); }}
        items={[
          { key: 'mine', label: '내가 검수할 항목' },
          { key: 'requested', label: '내가 요청한 항목' },
          { key: 'all', label: '전체' },
        ]}
      />

      {isLoading ? (
        <div className="flex h-64 items-center justify-center"><Spin /></div>
      ) : items.length > 0 ? (
        <div>
          {items.map(renderApprovalCard)}
          {(data?.meta?.total ?? 0) > 20 && (
            <div className="mt-4 text-center">
              <Button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="mr-2"
              >
                이전
              </Button>
              <Text type="secondary">페이지 {page}</Text>
              <Button
                disabled={items.length < 20}
                onClick={() => setPage((p) => p + 1)}
                className="ml-2"
              >
                다음
              </Button>
            </div>
          )}
        </div>
      ) : (
        <Empty description="승인 대기 항목이 없습니다" />
      )}
    </div>
  );
}
