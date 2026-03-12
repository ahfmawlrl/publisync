import { ArrowLeftOutlined, CloudUploadOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, SendOutlined, StopOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { App, Button, Card, Descriptions, Empty, Image, Popconfirm, Space, Spin, Tabs, Tag, Timeline, Typography } from 'antd';
import { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router';

import apiClient from '@/shared/api/client';
import type { PaginatedResponse } from '@/shared/api/types';
import MediaThumbnail from '@/shared/components/MediaThumbnail';
import { getStatusConfig } from '@/shared/constants/contentStatus';
import { CONTENT_MESSAGES } from '@/shared/constants/messages';
import { getPlatformConfig } from '@/shared/constants/platform';
import { useCancelPublish, useContent, useDeleteContent, usePublishContent, usePublishHistory, useRequestReview, useRetryPublish } from '../hooks/useContents';

interface ApprovalHistoryItem {
  id: string;
  action: string;
  reviewer_id: string | null;
  comment: string | null;
  created_at: string;
}

interface ApprovalRequestItem {
  id: string;
  content_id: string;
  status: string;
  requested_by: string;
  comment: string | null;
  histories: ApprovalHistoryItem[];
  created_at: string;
}

const APPROVAL_ACTION_CONFIG: Record<string, { text: string; color: string }> = {
  SUBMIT: { text: '검토 요청', color: 'blue' },
  APPROVE: { text: '승인', color: 'green' },
  REJECT: { text: '반려', color: 'red' },
  REQUEST_CHANGES: { text: '수정 요청', color: 'orange' },
};

const { Title, Paragraph, Text } = Typography;

export default function ContentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const { data: content, isLoading } = useContent(id ?? null);
  const { data: publishHistory } = usePublishHistory(id ?? null);
  const { data: approvalData } = useQuery({
    queryKey: ['approvals', 'by-content', id],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ApprovalRequestItem>>('/approvals', {
        params: { content_id: id, limit: 50 },
      });
      return res.data.data;
    },
    enabled: !!id,
  });
  const reviewMutation = useRequestReview();
  const deleteMutation = useDeleteContent();
  const publishMutation = usePublishContent();
  const cancelPublishMutation = useCancelPublish();
  const retryPublishMutation = useRetryPublish();

  const approvalTimelineItems = useMemo(() => {
    if (!approvalData || approvalData.length === 0) return null;
    const items: Array<{ color: string; children: React.ReactNode }> = [];
    for (const req of approvalData) {
      items.push({
        color: 'blue',
        children: (
          <div>
            <Text strong>검토 요청</Text>
            {req.comment && <div className="text-xs text-gray-500">{req.comment}</div>}
            <div className="text-xs text-gray-400">
              {new Date(req.created_at).toLocaleString('ko-KR')}
            </div>
          </div>
        ),
      });
      for (const h of req.histories) {
        const cfg = APPROVAL_ACTION_CONFIG[h.action] || { text: h.action, color: 'gray' };
        items.push({
          color: cfg.color,
          children: (
            <div>
              <Text strong>{cfg.text}</Text>
              {h.comment && <div className="text-xs text-gray-500">{h.comment}</div>}
              <div className="text-xs text-gray-400">
                {new Date(h.created_at).toLocaleString('ko-KR')}
              </div>
            </div>
          ),
        });
      }
    }
    return items;
  }, [approvalData]);

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Spin size="large" /></div>;
  }

  if (!content) {
    return <div className="p-6"><Title level={4}>콘텐츠를 찾을 수 없습니다</Title></div>;
  }

  const statusCfg = getStatusConfig(content.status);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Space>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/contents')} />
          <Title level={4} className="!mb-0">{content.title}</Title>
          <Tag color={statusCfg.color}>{statusCfg.text}</Tag>
        </Space>
        <Space>
          {['DRAFT', 'REJECTED'].includes(content.status) && (
            <Button icon={<EditOutlined />} onClick={() => navigate(`/contents/${id}/edit`)}>수정</Button>
          )}
          {content.status === 'DRAFT' && (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => {
                reviewMutation.mutate(content.id, {
                  onSuccess: () => message.success(CONTENT_MESSAGES.REQUEST_REVIEW_SUCCESS),
                  onError: () => message.error(CONTENT_MESSAGES.REQUEST_REVIEW_ERROR),
                });
              }}
            >
              검토 요청
            </Button>
          )}
          {content.status === 'APPROVED' && (
            <Popconfirm
              title="선택한 플랫폼에 콘텐츠를 게시하시겠습니까?"
              onConfirm={() => {
                publishMutation.mutate(content.id, {
                  onSuccess: () => message.success('게시가 완료되었습니다'),
                  onError: () => message.error('게시에 실패했습니다'),
                });
              }}
              okText="게시"
              cancelText="취소"
            >
              <Button type="primary" icon={<CloudUploadOutlined />} loading={publishMutation.isPending}>
                게시
              </Button>
            </Popconfirm>
          )}
          {content.status === 'SCHEDULED' && (
            <Popconfirm
              title="게시를 취소하시겠습니까?"
              onConfirm={() => {
                cancelPublishMutation.mutate(content.id, {
                  onSuccess: () => message.success(CONTENT_MESSAGES.CANCEL_PUBLISH_SUCCESS),
                  onError: () => message.error(CONTENT_MESSAGES.CANCEL_PUBLISH_ERROR),
                });
              }}
              okText="취소"
              cancelText="유지"
            >
              <Button danger icon={<StopOutlined />} loading={cancelPublishMutation.isPending}>
                게시 취소
              </Button>
            </Popconfirm>
          )}
          {['PUBLISH_FAILED', 'PARTIALLY_PUBLISHED'].includes(content.status) && (
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              loading={retryPublishMutation.isPending}
              onClick={() => {
                retryPublishMutation.mutate(content.id, {
                  onSuccess: () => message.success('게시 재시도가 요청되었습니다'),
                  onError: () => message.error('게시 재시도에 실패했습니다'),
                });
              }}
            >
              게시 재시도
            </Button>
          )}
          {['DRAFT', 'REJECTED'].includes(content.status) && (
            <Popconfirm
              title={CONTENT_MESSAGES.DELETE_CONFIRM}
              onConfirm={() => {
                deleteMutation.mutate(content.id, {
                  onSuccess: () => {
                    message.success(CONTENT_MESSAGES.DELETE_SUCCESS);
                    navigate('/contents');
                  },
                  onError: () => message.error(CONTENT_MESSAGES.DELETE_ERROR),
                });
              }}
              okText="삭제"
              cancelText="취소"
            >
              <Button danger icon={<DeleteOutlined />}>삭제</Button>
            </Popconfirm>
          )}
        </Space>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Tabs
            defaultActiveKey="content"
            items={[
              {
                key: 'content',
                label: '콘텐츠 내용',
                children: (
                  <div className="space-y-4">
                    <Card title="본문">
                      <Paragraph>{content.body || '(본문 없음)'}</Paragraph>
                    </Card>
                    {content.media_urls && content.media_urls.length > 0 && (
                      <Card title="미디어" size="small">
                        <Image.PreviewGroup>
                          <div className="flex flex-wrap gap-2">
                            {content.media_urls.map((url, idx) => (
                              <MediaThumbnail key={idx} src={url} alt={`미디어 ${idx + 1}`} />
                            ))}
                          </div>
                        </Image.PreviewGroup>
                      </Card>
                    )}
                    <Card title="정보" size="small">
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="플랫폼">
                          <Space wrap>{content.platforms.map((p) => <Tag key={p} color={getPlatformConfig(p).color}>{getPlatformConfig(p).label}</Tag>)}</Space>
                        </Descriptions.Item>
                        <Descriptions.Item label="예약일시">
                          {content.scheduled_at ? new Date(content.scheduled_at).toLocaleString('ko-KR') : '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="AI 생성">
                          {content.ai_generated ? '예' : '아니오'}
                        </Descriptions.Item>
                        <Descriptions.Item label="작성일">
                          {new Date(content.created_at).toLocaleString('ko-KR')}
                        </Descriptions.Item>
                        <Descriptions.Item label="수정일">
                          {new Date(content.updated_at).toLocaleString('ko-KR')}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </div>
                ),
              },
              {
                key: 'preview',
                label: '플랫폼별 미리보기',
                children: (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {content.platforms.includes('YOUTUBE') && (
                      <Card size="small" title={<Tag color="red">YouTube</Tag>}>
                        <div className="mb-2 flex h-32 items-center justify-center rounded bg-gray-100 text-gray-400">
                          영상 미리보기
                        </div>
                        <Text strong className="text-sm">{content.title}</Text>
                        <br />
                        <Text type="secondary" className="text-xs">
                          {(content.body || '').slice(0, 60) || '본문 없음'}
                        </Text>
                      </Card>
                    )}
                    {content.platforms.includes('INSTAGRAM') && (
                      <Card size="small" title={<Tag color="purple">Instagram</Tag>}>
                        <div className="mb-2 flex h-32 items-center justify-center rounded bg-gray-100 text-gray-400">
                          이미지 미리보기
                        </div>
                        <Text className="text-xs">
                          {(content.body || '').slice(0, 80) || '설명문 없음'}
                        </Text>
                      </Card>
                    )}
                    {content.platforms.includes('FACEBOOK') && (
                      <Card size="small" title={<Tag color="blue">Facebook</Tag>}>
                        <div className="mb-2 flex h-32 items-center justify-center rounded bg-gray-100 text-gray-400">
                          피드 미리보기
                        </div>
                        <Text strong className="text-sm">{content.title}</Text>
                        <br />
                        <Text type="secondary" className="text-xs">
                          {(content.body || '').slice(0, 100) || '본문 없음'}
                        </Text>
                      </Card>
                    )}
                    {content.platforms.includes('X') && (
                      <Card size="small" title={<Tag>X (Twitter)</Tag>}>
                        <Text className="text-sm">
                          {(content.body || '').slice(0, 280) || '본문 없음'}
                        </Text>
                      </Card>
                    )}
                    {content.platforms.includes('NAVER_BLOG') && (
                      <Card size="small" title={<Tag color="green">네이버 블로그</Tag>}>
                        <Text strong className="text-sm">{content.title}</Text>
                        <br />
                        <Text type="secondary" className="text-xs">
                          {(content.body || '').slice(0, 120) || '본문 없음'}
                        </Text>
                      </Card>
                    )}
                    {content.platforms.length === 0 && (
                      <Empty description="선택된 플랫폼이 없습니다" />
                    )}
                  </div>
                ),
              },
              {
                key: 'publish-history',
                label: '게시 이력',
                children: publishHistory && publishHistory.data.length > 0 ? (
                  <Card size="small">
                    <Timeline
                      items={publishHistory.data.map((pr) => ({
                        color: pr.status === 'SUCCESS' ? 'green' : pr.status === 'FAILED' ? 'red' : 'blue',
                        children: (
                          <div>
                            <Tag color={pr.status === 'SUCCESS' ? 'green' : pr.status === 'FAILED' ? 'red' : 'blue'}>
                              {pr.status}
                            </Tag>
                            {pr.platform_url && (
                              <a href={pr.platform_url} target="_blank" rel="noopener noreferrer" className="text-xs">
                                링크
                              </a>
                            )}
                            <div className="text-xs text-gray-400">
                              {new Date(pr.created_at).toLocaleString('ko-KR')}
                            </div>
                            {pr.error_message && <div className="text-xs text-red-500">{pr.error_message}</div>}
                          </div>
                        ),
                      }))}
                    />
                  </Card>
                ) : (
                  <Empty description="게시 이력이 없습니다" />
                ),
              },
              {
                key: 'approval-history',
                label: '승인 이력',
                children: approvalTimelineItems && approvalTimelineItems.length > 0 ? (
                  <Card size="small">
                    <Timeline items={approvalTimelineItems} />
                  </Card>
                ) : (
                  <Empty description="승인 이력이 없습니다" />
                ),
              },
            ]}
          />
        </div>

        <div className="space-y-4">
          <Card title="요약" size="small">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="상태">
                <Tag color={statusCfg.color}>{statusCfg.text}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="플랫폼">
                <Space wrap>{content.platforms.map((p) => <Tag key={p} color={getPlatformConfig(p).color} className="text-xs">{getPlatformConfig(p).label}</Tag>)}</Space>
              </Descriptions.Item>
              <Descriptions.Item label="예약일시">
                {content.scheduled_at ? new Date(content.scheduled_at).toLocaleString('ko-KR') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="AI 생성">
                {content.ai_generated ? '예' : '아니오'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </div>
      </div>
    </div>
  );
}
