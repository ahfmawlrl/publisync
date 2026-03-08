import { ArrowLeftOutlined, EditOutlined, SendOutlined } from '@ant-design/icons';
import { App, Button, Card, Descriptions, Empty, Space, Spin, Tabs, Tag, Timeline, Typography } from 'antd';
import { useNavigate, useParams } from 'react-router';

import { useContent, usePublishHistory, useRequestReview } from '../hooks/useContents';

const { Title, Paragraph, Text } = Typography;

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

export default function ContentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const { data: content, isLoading } = useContent(id ?? null);
  const { data: publishHistory } = usePublishHistory(id ?? null);
  const reviewMutation = useRequestReview();

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Spin size="large" /></div>;
  }

  if (!content) {
    return <div className="p-6"><Title level={4}>콘텐츠를 찾을 수 없습니다</Title></div>;
  }

  const statusCfg = STATUS_CONFIG[content.status] || { color: 'default', text: content.status };

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
                  onSuccess: () => message.success('검토 요청 완료'),
                  onError: () => message.error('검토 요청 실패'),
                });
              }}
            >
              검토 요청
            </Button>
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
                    <Card title="정보" size="small">
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="플랫폼">
                          <Space wrap>{content.platforms.map((p) => <Tag key={p} color={PLATFORM_COLORS[p]}>{PLATFORM_LABELS[p] || p}</Tag>)}</Space>
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
                children: (
                  <Card size="small">
                    <Timeline
                      items={[
                        {
                          color: 'blue',
                          children: (
                            <div>
                              <Text strong>콘텐츠 작성</Text>
                              <div className="text-xs text-gray-400">
                                {new Date(content.created_at).toLocaleString('ko-KR')}
                              </div>
                            </div>
                          ),
                        },
                        ...(content.status !== 'DRAFT'
                          ? [
                              {
                                color: 'orange' as const,
                                children: (
                                  <div>
                                    <Text strong>검토 요청</Text>
                                    <div className="text-xs text-gray-400">
                                      상태: {STATUS_CONFIG[content.status]?.text || content.status}
                                    </div>
                                  </div>
                                ),
                              },
                            ]
                          : []),
                        ...(content.status === 'APPROVED' || content.status === 'PUBLISHED' || content.status === 'SCHEDULED'
                          ? [
                              {
                                color: 'green' as const,
                                children: (
                                  <div>
                                    <Text strong>승인 완료</Text>
                                  </div>
                                ),
                              },
                            ]
                          : []),
                        ...(content.status === 'REJECTED'
                          ? [
                              {
                                color: 'red' as const,
                                children: (
                                  <div>
                                    <Text strong>반려됨</Text>
                                  </div>
                                ),
                              },
                            ]
                          : []),
                        ...(content.status === 'PUBLISHED'
                          ? [
                              {
                                color: 'green' as const,
                                children: (
                                  <div>
                                    <Text strong>게시 완료</Text>
                                  </div>
                                ),
                              },
                            ]
                          : []),
                      ]}
                    />
                  </Card>
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
                <Space wrap>{content.platforms.map((p) => <Tag key={p} color={PLATFORM_COLORS[p]} className="text-xs">{PLATFORM_LABELS[p] || p}</Tag>)}</Space>
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
