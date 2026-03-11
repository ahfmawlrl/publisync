import { ArrowLeftOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Alert, App, Button, Card, Empty, Image, Input, Modal, Spin, Tabs, Tag, Typography } from 'antd';
import { useState } from 'react';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import MediaThumbnail from '@/shared/components/MediaThumbnail';
import { APPROVAL_STATUS_CONFIG } from '@/shared/constants/contentStatus';
import { APPROVAL_MESSAGES } from '@/shared/constants/messages';
import { getPlatformConfig } from '@/shared/constants/platform';
import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useApproval, useApprovals, useApproveRequest, useRejectRequest } from '../hooks/useApprovals';
import type { ApprovalRequestRecord } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

type TabKey = 'mine' | 'requested' | 'all';

export default function ApprovalsListPage() {
  const { message } = App.useApp();
  const currentUserId = useAuthStore((s) => s.user?.id);
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState<TabKey>('mine');
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState('');
  const [rejectModalId, setRejectModalId] = useState<string | null>(null);

  const statusFilter = activeTab === 'mine' ? 'PENDING_REVIEW' : undefined;
  const requestedByFilter = activeTab === 'requested' ? currentUserId : undefined;
  const { data, isLoading } = useApprovals({ page, status: statusFilter, requested_by: requestedByFilter });
  const { data: detailData, isLoading: detailLoading } = useApproval(reviewId);
  const approveMutation = useApproveRequest();
  const rejectMutation = useRejectRequest();

  // Fetch content body for approval detail view (inline to avoid cross-feature import)
  const contentId = detailData?.content_id;
  const { data: contentData } = useQuery({
    queryKey: ['content', contentId],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<{ id: string; title: string; body: string | null; media_urls: string[]; status: string; platforms: string[] }>>(`/contents/${contentId}`);
      return res.data.data;
    },
    enabled: !!contentId,
  });

  const handleApprove = (id: string) => {
    approveMutation.mutate(
      { id },
      {
        onSuccess: () => {
          message.success(APPROVAL_MESSAGES.APPROVE_SUCCESS);
          setReviewId(null);
        },
        onError: () => message.error(APPROVAL_MESSAGES.APPROVE_ERROR),
      },
    );
  };

  const handleReject = () => {
    if (!rejectModalId) return;
    rejectMutation.mutate(
      { id: rejectModalId, comment: rejectComment },
      {
        onSuccess: () => {
          message.success(APPROVAL_MESSAGES.REJECT_SUCCESS);
          setRejectModalId(null);
          setRejectComment('');
          setReviewId(null);
        },
        onError: () => message.error(APPROVAL_MESSAGES.REJECT_ERROR),
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
          <Tag color={APPROVAL_STATUS_CONFIG[record.status]?.color ?? 'default'}>
            {APPROVAL_STATUS_CONFIG[record.status]?.text ?? record.status}
          </Tag>
          {record.platforms && record.platforms.length > 0 && (
            <>
              {record.platforms.map((p) => {
                const pcfg = getPlatformConfig(p);
                return (
                  <Tag key={p} color={pcfg.color} className="text-xs">
                    {pcfg.label}
                  </Tag>
                );
              })}
            </>
          )}
        </div>
        <div className="text-xs text-gray-500">
          요청자: {record.requested_by_name || record.requested_by} · 요청일: {new Date(record.created_at).toLocaleString('ko-KR')}
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
            <Card title={contentData?.title ?? '콘텐츠 내용'}>
              {/* Media preview */}
              {contentData?.media_urls && contentData.media_urls.length > 0 ? (
                <div className="mb-3">
                  <Image.PreviewGroup>
                    <div className="flex flex-wrap gap-2">
                      {contentData.media_urls.map((url, idx) => (
                        <MediaThumbnail key={idx} src={url} alt={`미디어 ${idx + 1}`} width={120} height={120} />
                      ))}
                    </div>
                  </Image.PreviewGroup>
                </div>
              ) : (
                <div className="mb-3 flex h-32 items-center justify-center rounded bg-gray-100 text-gray-400">
                  첨부 미디어 없음
                </div>
              )}
              {/* Content body */}
              {contentData?.body && (
                <div className="mb-3 whitespace-pre-wrap rounded bg-gray-50 p-3 text-sm">
                  {contentData.body}
                </div>
              )}
              <div className="text-sm">
                <div className="mb-1"><Text strong>상태:</Text> {APPROVAL_STATUS_CONFIG[detailData.status]?.text ?? detailData.status}</div>
                <div className="mb-1"><Text strong>긴급:</Text> {detailData.is_urgent ? '예' : '아니오'}</div>
                {contentData?.platforms && contentData.platforms.length > 0 && (
                  <div className="mb-1 flex items-center gap-1">
                    <Text strong>플랫폼:</Text>
                    {contentData.platforms.map((p) => {
                      const pcfg = getPlatformConfig(p);
                      return <Tag key={p} color={pcfg.color} className="text-xs">{pcfg.label}</Tag>;
                    })}
                  </div>
                )}
              </div>
            </Card>

            {/* Right: Review panel */}
            <div className="space-y-4">
              <Card title="AI 검수 결과" size="small">
                <Alert
                  type="info"
                  showIcon
                  message="AI 자동 검수 기능은 Phase 2에서 지원될 예정입니다"
                  description="표현 적합성 검사, 개인정보 검출, 접근성 검사 등의 AI 기능이 추가됩니다."
                />
              </Card>

              <Card title="승인 이력" size="small">
                <div className="text-sm">
                  <div className="py-1">{new Date(detailData.created_at).toLocaleDateString('ko-KR')} 검토 요청 ({detailData.requested_by_name || detailData.requested_by})</div>
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
