import { ArrowLeftOutlined, CheckCircleOutlined, RobotOutlined, SwapOutlined, VideoCameraOutlined } from '@ant-design/icons';
import {
  App,
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  DatePicker,
  Divider,
  Form,
  Input,
  List,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import AiSuggestionPanel from '@/features/ai/components/AiSuggestionPanel';
import {
  useContentReview,
  useGenerateDescription,
  useGenerateHashtags,
  useGenerateTitle,
  useToneTransform,
} from '@/features/ai/hooks/useAi';
import MediaUpload from '@/shared/components/MediaUpload';
import { useCreateContent } from '../hooks/useContents';
import type { ContentCreateData } from '../types';

const { Title } = Typography;
const { TextArea } = Input;

const PLATFORM_OPTIONS = [
  { value: 'YOUTUBE', label: 'YouTube' },
  { value: 'INSTAGRAM', label: 'Instagram' },
  { value: 'FACEBOOK', label: 'Facebook' },
  { value: 'X', label: 'X (Twitter)' },
  { value: 'NAVER_BLOG', label: '네이버 블로그' },
];

export default function ContentCreatePage() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createMutation = useCreateContent();

  // G4: Reactive preview using Form.useWatch
  const watchedTitle = Form.useWatch('title', form);
  const watchedBody = Form.useWatch('body', form);
  const watchedHashtags = Form.useWatch('hashtags', form);

  // AI mutations
  const titleMutation = useGenerateTitle();
  const descriptionMutation = useGenerateDescription();
  const hashtagMutation = useGenerateHashtags();
  const toneTransformMutation = useToneTransform();
  const contentReviewMutation = useContentReview();

  // Tone transform modal
  const [toneModalOpen, setToneModalOpen] = useState(false);
  const [tonePlatform, setTonePlatform] = useState<string>('YOUTUBE');
  const [toneTone, setToneTone] = useState<string>('casual');

  // Content review modal (kept for launching reviews)
  const [reviewModalOpen, setReviewModalOpen] = useState(false);

  const handleSubmit = async (values: Record<string, unknown>) => {
    const data: ContentCreateData = {
      title: values.title as string,
      body: values.body as string | undefined,
      platforms: (values.platforms as string[]) || [],
      channel_ids: [],
      media_urls: (values.media_urls as string[]) || [],
    };

    if (values.scheduled_at) {
      data.scheduled_at = (values.scheduled_at as { toISOString: () => string }).toISOString();
    }

    // Mark as AI-generated if any AI suggestion was used
    if (titleMutation.data || descriptionMutation.data || hashtagMutation.data) {
      data.ai_generated = true;
    }

    try {
      await createMutation.mutateAsync(data);
      message.success('콘텐츠가 작성되었습니다');
      navigate('/contents');
    } catch {
      message.error('콘텐츠 작성에 실패했습니다');
    }
  };

  /** Get the current body text for AI requests. */
  const getContentText = (): string | null => {
    const body = form.getFieldValue('body') as string | undefined;
    if (!body || body.trim().length < 10) {
      message.warning('AI 제안을 받으려면 본문을 10자 이상 입력하세요.');
      return null;
    }
    return body.trim();
  };

  /** Get the first selected platform (if any). */
  const getSelectedPlatform = (): string | undefined => {
    const platforms = form.getFieldValue('platforms') as string[] | undefined;
    return platforms?.[0];
  };

  const handleGenerateTitle = () => {
    const contentText = getContentText();
    if (!contentText) return;
    titleMutation.mutate({
      content_text: contentText,
      platform: getSelectedPlatform(),
      count: 3,
    });
  };

  const handleGenerateDescription = () => {
    const contentText = getContentText();
    if (!contentText) return;
    descriptionMutation.mutate({
      content_text: contentText,
      platform: getSelectedPlatform(),
      count: 2,
    });
  };

  const handleGenerateHashtags = () => {
    const contentText = getContentText();
    if (!contentText) return;
    hashtagMutation.mutate({
      content_text: contentText,
      platform: getSelectedPlatform(),
      count: 5,
    });
  };

  const handleToneTransform = () => {
    const contentText = getContentText();
    if (!contentText) return;
    setToneModalOpen(true);
    toneTransformMutation.mutate(
      {
        content_text: contentText,
        target_platform: tonePlatform,
        target_tone: toneTone,
        count: 2,
      },
      { onError: () => message.error('AI 톤 변환에 실패했습니다') },
    );
  };

  const handleToneTransformRerun = () => {
    const contentText = getContentText();
    if (!contentText) return;
    toneTransformMutation.mutate(
      {
        content_text: contentText,
        target_platform: tonePlatform,
        target_tone: toneTone,
        count: 2,
      },
      { onError: () => message.error('AI 톤 변환에 실패했습니다') },
    );
  };

  const handleContentReview = () => {
    const contentText = getContentText();
    if (!contentText) return;
    setReviewModalOpen(true);
    contentReviewMutation.mutate(
      {
        content_text: contentText,
        check_spelling: true,
        check_sensitivity: true,
        check_bias: true,
      },
      {
        onSuccess: () => {
          // Close modal after successful review, results will show inline
          setReviewModalOpen(false);
        },
        onError: () => message.error('AI 검수에 실패했습니다'),
      },
    );
  };

  // G4: Preview display values from watched fields
  const previewTitle = watchedTitle || '제목을 입력하세요';
  const previewBody = watchedBody || '';
  const previewHashtags = watchedHashtags || '#해시태그';

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/contents')} />
          <Title level={4} className="!mb-0">새 콘텐츠 작성</Title>
        </div>
        <Space>
          <Button onClick={() => navigate('/contents')}>임시 저장</Button>
          <Button type="primary">검토 요청</Button>
        </Space>
      </div>

      <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ platforms: [] }}>
        <div className="mb-4">
          <Form.Item name="platforms" className="!mb-0">
            <Checkbox.Group options={PLATFORM_OPTIONS} />
          </Form.Item>
        </div>

      <Row gutter={24}>
        {/* Left: Content form */}
        <Col xs={24} lg={16}>
          <Card>
              <Form.Item name="media_urls" label="미디어 업로드">
                <MediaUpload maxFiles={10} />
              </Form.Item>

              <Form.Item
                name="title"
                label="제목"
                rules={[{ required: true, message: '제목을 입력하세요' }]}
                extra={
                  <Button
                    type="link"
                    size="small"
                    icon={<RobotOutlined />}
                    onClick={handleGenerateTitle}
                    loading={titleMutation.isPending}
                    className="mt-1 !p-0"
                  >
                    AI 제목 제안
                  </Button>
                }
              >
                <Input placeholder="콘텐츠 제목" maxLength={500} showCount />
              </Form.Item>

              <Form.Item name="body" label="본문/설명문">
                <TextArea rows={8} placeholder="콘텐츠 본문을 작성하세요" />
              </Form.Item>

              <Form.Item
                name="hashtags"
                label="해시태그"
                extra={
                  <Button
                    type="link"
                    size="small"
                    icon={<RobotOutlined />}
                    onClick={handleGenerateHashtags}
                    loading={hashtagMutation.isPending}
                    className="mt-1 !p-0"
                  >
                    AI 해시태그 추천
                  </Button>
                }
              >
                <Input placeholder="#서울시 #정책브리핑 #3월" />
              </Form.Item>

              <Form.Item name="scheduled_at" label="예약 게시일시">
                <DatePicker showTime format="YYYY-MM-DD HH:mm" placeholder="예약 게시 (선택)" className="w-full" />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
                    저장 (초안)
                  </Button>
                  <Button onClick={() => navigate('/contents')}>취소</Button>
                </Space>
              </Form.Item>
          </Card>
        </Col>

        {/* Right: Preview + AI panels */}
        <Col xs={24} lg={8}>
          {/* G4: Platform preview with reactive watched values */}
          <Card title="플랫폼별 미리보기" size="small" className="mb-4">
            <Tabs
              size="small"
              items={[
                {
                  key: 'youtube',
                  label: 'YouTube',
                  children: (
                    <div>
                      <div className="mb-2 flex h-36 items-center justify-center rounded bg-gray-100 text-gray-400">
                        영상 미리보기
                      </div>
                      <Typography.Text strong className="text-sm">
                        {previewTitle}
                      </Typography.Text>
                      <br />
                      <Typography.Text type="secondary" className="text-xs">
                        {previewBody.slice(0, 60) || '본문 미리보기...'}
                      </Typography.Text>
                      <br />
                      <Typography.Text className="text-xs" style={{ color: '#1677ff' }}>
                        {previewHashtags}
                      </Typography.Text>
                    </div>
                  ),
                },
                {
                  key: 'instagram',
                  label: 'Instagram',
                  children: (
                    <div>
                      <div className="mb-2 flex h-36 items-center justify-center rounded bg-gray-100 text-gray-400">
                        이미지 미리보기
                      </div>
                      <Typography.Text className="text-xs">
                        {previewBody.slice(0, 80) || '설명문 미리보기...'}
                      </Typography.Text>
                    </div>
                  ),
                },
                {
                  key: 'facebook',
                  label: 'Facebook',
                  children: (
                    <div>
                      <div className="mb-2 flex h-36 items-center justify-center rounded bg-gray-100 text-gray-400">
                        피드 미리보기
                      </div>
                      <Typography.Text strong className="text-sm">
                        {previewTitle}
                      </Typography.Text>
                      <br />
                      <Typography.Text type="secondary" className="text-xs">
                        {previewBody.slice(0, 100) || '본문 미리보기...'}
                      </Typography.Text>
                    </div>
                  ),
                },
              ]}
            />
          </Card>

          {/* AI assistant */}
          <Card
            title={
              <Space>
                <RobotOutlined />
                <span>AI 어시스턴트</span>
              </Space>
            }
            size="small"
          >
            <Space direction="vertical" className="w-full" size={16}>
              {/* Title suggestions */}
              <div>
                <Button
                  type="default"
                  icon={<RobotOutlined />}
                  onClick={handleGenerateTitle}
                  loading={titleMutation.isPending}
                  block
                >
                  제목 제안 받기
                </Button>
                <div className="mt-2">
                  <AiSuggestionPanel
                    title="AI 제목 제안"
                    suggestions={titleMutation.data?.suggestions ?? []}
                    loading={titleMutation.isPending}
                    onSelect={(content) => form.setFieldValue('title', content)}
                    error={titleMutation.data?.error}
                    model={titleMutation.data?.model}
                    processingTimeMs={titleMutation.data?.processing_time_ms}
                  />
                </div>
              </div>

              <Divider className="!my-2" />

              {/* Description suggestions */}
              <div>
                <Button
                  type="default"
                  icon={<RobotOutlined />}
                  onClick={handleGenerateDescription}
                  loading={descriptionMutation.isPending}
                  block
                >
                  설명문 제안 받기
                </Button>
                <div className="mt-2">
                  <AiSuggestionPanel
                    title="AI 설명문 제안"
                    suggestions={descriptionMutation.data?.suggestions ?? []}
                    loading={descriptionMutation.isPending}
                    onSelect={(content) => {
                      const currentBody = (form.getFieldValue('body') as string) || '';
                      form.setFieldValue('body', currentBody ? `${currentBody}\n\n${content}` : content);
                    }}
                    error={descriptionMutation.data?.error}
                    model={descriptionMutation.data?.model}
                    processingTimeMs={descriptionMutation.data?.processing_time_ms}
                  />
                </div>
              </div>

              <Divider className="!my-2" />

              {/* Hashtag suggestions */}
              <div>
                <Button
                  type="default"
                  icon={<RobotOutlined />}
                  onClick={handleGenerateHashtags}
                  loading={hashtagMutation.isPending}
                  block
                >
                  해시태그 제안 받기
                </Button>
                <div className="mt-2">
                  <AiSuggestionPanel
                    title="AI 해시태그 제안"
                    suggestions={hashtagMutation.data?.suggestions ?? []}
                    loading={hashtagMutation.isPending}
                    onSelect={(content) => {
                      const currentBody = (form.getFieldValue('body') as string) || '';
                      const hashtag = content.startsWith('#') ? content : `#${content}`;
                      form.setFieldValue('body', currentBody ? `${currentBody} ${hashtag}` : hashtag);
                    }}
                    error={hashtagMutation.data?.error}
                    model={hashtagMutation.data?.model}
                    processingTimeMs={hashtagMutation.data?.processing_time_ms}
                  />
                </div>
              </div>

              <Divider className="!my-2" />

              {/* Tone transform (S17, F17) */}
              <div>
                <Button
                  type="default"
                  icon={<SwapOutlined />}
                  onClick={handleToneTransform}
                  loading={toneTransformMutation.isPending}
                  block
                >
                  AI 톤 변환
                </Button>
              </div>

              <Divider className="!my-2" />

              {/* Content review (S17, F21) */}
              <div>
                <Button
                  type="default"
                  icon={<CheckCircleOutlined />}
                  onClick={handleContentReview}
                  loading={contentReviewMutation.isPending}
                  block
                >
                  AI 콘텐츠 검수
                </Button>
              </div>
            </Space>
          </Card>

          {/* G6: AI Review Inline Card - persistent results display */}
          <Card
            title={
              <Space>
                <CheckCircleOutlined />
                <span>AI 검수 결과</span>
              </Space>
            }
            size="small"
            className="mt-4"
          >
            {contentReviewMutation.isPending && (
              <div className="flex items-center justify-center py-4">
                <Space>
                  <Spin size="small" />
                  <Typography.Text type="secondary">
                    AI가 콘텐츠를 검수하고 있습니다...
                  </Typography.Text>
                </Space>
              </div>
            )}

            {!contentReviewMutation.data && !contentReviewMutation.isPending && (
              <Typography.Text type="secondary" className="text-xs">
                위의 &quot;AI 콘텐츠 검수&quot; 버튼을 클릭하면 검수 결과가 여기에 표시됩니다.
              </Typography.Text>
            )}

            {contentReviewMutation.data?.error && !contentReviewMutation.isPending && (
              <Alert type="warning" message={contentReviewMutation.data.error} showIcon />
            )}

            {contentReviewMutation.data && !contentReviewMutation.isPending && !contentReviewMutation.data.error && (
              <div>
                <Alert
                  type={contentReviewMutation.data.issues.length > 0 ? 'warning' : 'success'}
                  message={contentReviewMutation.data.summary}
                  showIcon
                  className="mb-3"
                />

                {contentReviewMutation.data.model && (
                  <div className="mb-2 flex items-center gap-2">
                    <Tag color="blue">{contentReviewMutation.data.model}</Tag>
                    {contentReviewMutation.data.processing_time_ms !== undefined && (
                      <Typography.Text type="secondary" className="text-xs">
                        {(contentReviewMutation.data.processing_time_ms / 1000).toFixed(1)}s
                      </Typography.Text>
                    )}
                  </div>
                )}

                {contentReviewMutation.data.issues.length > 0 && (
                  <List
                    size="small"
                    dataSource={contentReviewMutation.data.issues}
                    renderItem={(issue, index) => (
                      <List.Item key={index} className="!px-0">
                        <div>
                          <Space size={4}>
                            <Tag
                              color={
                                issue.severity === 'HIGH'
                                  ? 'red'
                                  : issue.severity === 'MEDIUM'
                                    ? 'orange'
                                    : 'default'
                              }
                            >
                              {issue.severity}
                            </Tag>
                            <Typography.Text className="text-xs">{issue.issue}</Typography.Text>
                          </Space>
                          {issue.suggestion && (
                            <div className="mt-1 pl-1">
                              <Typography.Text type="secondary" className="text-xs">
                                제안: {issue.suggestion}
                              </Typography.Text>
                            </div>
                          )}
                        </div>
                      </List.Item>
                    )}
                  />
                )}

                <Typography.Text type="secondary" className="mt-2 block text-xs">
                  AI가 생성한 검수 결과입니다. 최종 판단은 사용자가 합니다.
                </Typography.Text>
              </div>
            )}
          </Card>

          {/* Video content features */}
          <Card
            title={
              <Space>
                <VideoCameraOutlined />
                <span>영상 콘텐츠 추가 기능</span>
              </Space>
            }
            size="small"
            className="mt-4"
          >
            <div className="flex flex-wrap gap-2">
              <Button size="small" icon={<RobotOutlined />} disabled>
                자막 자동 생성 (F03)
              </Button>
              <Button size="small" icon={<RobotOutlined />} disabled>
                숏폼 생성 (F15)
              </Button>
              <Button size="small" icon={<RobotOutlined />} disabled>
                효과음/이모지 추천
              </Button>
            </div>
            <Typography.Text type="secondary" className="mt-2 block text-xs">
              Phase 2에서 활성화됩니다
            </Typography.Text>
          </Card>
        </Col>
      </Row>

      {/* Workflow progress bar */}
      <div className="mt-4 flex items-center justify-center gap-2 rounded bg-gray-50 py-3 text-sm">
        <span className="font-medium text-blue-600">● 작성 중</span>
        <span className="text-gray-400">→</span>
        <span className="text-gray-400">○ 검토 요청</span>
        <span className="text-gray-400">→</span>
        <span className="text-gray-400">○ 검수 중</span>
        <span className="text-gray-400">→</span>
        <span className="text-gray-400">○ 게시</span>
      </div>
      </Form>

      {/* Tone Transform Modal (S17, F17) */}
      <Modal
        title={
          <Space>
            <SwapOutlined />
            <span>AI 톤 변환</span>
          </Space>
        }
        open={toneModalOpen}
        onCancel={() => {
          setToneModalOpen(false);
          toneTransformMutation.reset();
        }}
        footer={null}
        width={640}
      >
        <div className="mb-4 flex items-center gap-3">
          <Select
            value={tonePlatform}
            onChange={setTonePlatform}
            style={{ width: 160 }}
            options={PLATFORM_OPTIONS}
          />
          <Select
            value={toneTone}
            onChange={setToneTone}
            style={{ width: 140 }}
            options={[
              { value: 'formal', label: '공식적' },
              { value: 'casual', label: '캐주얼' },
              { value: 'friendly', label: '친근한' },
              { value: 'professional', label: '전문적' },
            ]}
          />
          <Button
            type="primary"
            onClick={handleToneTransformRerun}
            loading={toneTransformMutation.isPending}
          >
            변환하기
          </Button>
        </div>

        {toneTransformMutation.isPending && (
          <div className="flex items-center justify-center py-8">
            <Space>
              <Spin size="small" />
              <Typography.Text type="secondary">
                AI가 콘텐츠를 변환하고 있습니다...
              </Typography.Text>
            </Space>
          </div>
        )}

        {toneTransformMutation.data?.error && (
          <Alert type="warning" message={toneTransformMutation.data.error} showIcon className="mb-4" />
        )}

        {toneTransformMutation.data?.suggestions && toneTransformMutation.data.suggestions.length > 0 && (
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Typography.Text strong>변환 결과</Typography.Text>
              {toneTransformMutation.data.model && (
                <Tag color="blue">{toneTransformMutation.data.model}</Tag>
              )}
            </div>
            <List
              size="small"
              dataSource={toneTransformMutation.data.suggestions}
              renderItem={(item, index) => (
                <List.Item
                  key={index}
                  actions={[
                    <Button
                      key="use"
                      type="link"
                      size="small"
                      onClick={() => {
                        form.setFieldValue('body', item.content);
                        setToneModalOpen(false);
                        message.success('변환된 콘텐츠가 본문에 적용되었습니다');
                      }}
                    >
                      적용하기
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={<Typography.Text className="text-sm">{item.content}</Typography.Text>}
                    description={
                      <Progress
                        percent={Math.round(item.score * 100)}
                        size="small"
                        className="!mb-0 w-24"
                        format={(p) => `${p}%`}
                      />
                    }
                  />
                </List.Item>
              )}
            />
            <Typography.Text type="secondary" className="mt-2 block text-xs">
              AI가 생성한 제안입니다. 최종 결정은 사용자가 합니다.
            </Typography.Text>
          </div>
        )}
      </Modal>

      {/* Content Review Modal - now only shows loading spinner while processing */}
      <Modal
        title={
          <Space>
            <CheckCircleOutlined />
            <span>AI 콘텐츠 검수</span>
          </Space>
        }
        open={reviewModalOpen}
        onCancel={() => {
          setReviewModalOpen(false);
        }}
        footer={null}
        width={400}
      >
        <div className="flex items-center justify-center py-8">
          <Space>
            <Spin size="small" />
            <Typography.Text type="secondary">
              AI가 콘텐츠를 검수하고 있습니다...
            </Typography.Text>
          </Space>
        </div>
        <Typography.Text type="secondary" className="block text-center text-xs">
          완료되면 결과가 우측 패널에 표시됩니다.
        </Typography.Text>
      </Modal>
    </div>
  );
}
