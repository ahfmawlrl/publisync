import { ArrowLeftOutlined, EditOutlined, SendOutlined } from '@ant-design/icons';
import { App, Button, Card, Descriptions, Space, Spin, Tag, Timeline, Typography } from 'antd';
import { useNavigate, useParams } from 'react-router';

import { useContent, usePublishHistory, useRequestReview } from '../hooks/useContents';

const { Title, Paragraph } = Typography;

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
          <Card title="본문">
            <Paragraph>{content.body || '(본문 없음)'}</Paragraph>
          </Card>
        </div>

        <div className="space-y-4">
          <Card title="정보" size="small">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="플랫폼">
                <Space wrap>{content.platforms.map((p) => <Tag key={p}>{p}</Tag>)}</Space>
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

          {publishHistory && publishHistory.data.length > 0 && (
            <Card title="게시 이력" size="small">
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
          )}
        </div>
      </div>
    </div>
  );
}
