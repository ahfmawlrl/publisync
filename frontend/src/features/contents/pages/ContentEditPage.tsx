import { ArrowLeftOutlined, CheckCircleOutlined, PictureOutlined, RobotOutlined, SendOutlined, SwapOutlined, TranslationOutlined, VideoCameraOutlined } from '@ant-design/icons';
import {
  Alert,
  App,
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
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router';

import AiSuggestionPanel from '@/features/ai/components/AiSuggestionPanel';
import {
  useContentReview,
  useGenerateDescription,
  useGenerateHashtags,
  useGenerateTitle,
  useSuggestEffects,
  useToneTransform,
  useTranslate,
} from '@/features/ai/hooks/useAi';
import { useCreateThumbnail, useJobStatus } from '@/features/ai/hooks/useAiJobs';
import MediaUpload from '@/shared/components/MediaUpload';
import { CONTENT_MESSAGES } from '@/shared/constants/messages';
import { useContent, useRequestReview, useSaveDraft, useUpdateContent } from '../hooks/useContents';

const { Title } = Typography;
const { TextArea } = Input;

const PLATFORM_OPTIONS = [
  { value: 'YOUTUBE', label: 'YouTube' },
  { value: 'INSTAGRAM', label: 'Instagram' },
  { value: 'FACEBOOK', label: 'Facebook' },
  { value: 'X', label: 'X (Twitter)' },
  { value: 'NAVER_BLOG', label: '네이버 블로그' },
];

export default function ContentEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const { data: content, isLoading } = useContent(id ?? null);
  const updateMutation = useUpdateContent();
  const saveDraftMutation = useSaveDraft();
  const reviewMutation = useRequestReview();

  // G4: Reactive preview
  const watchedTitle = Form.useWatch('title', form);
  const watchedBody = Form.useWatch('body', form);
  const watchedHashtags = Form.useWatch('hashtags', form);

  // AI mutations
  const titleMutation = useGenerateTitle();
  const descriptionMutation = useGenerateDescription();
  const hashtagMutation = useGenerateHashtags();
  const toneTransformMutation = useToneTransform();
  const contentReviewMutation = useContentReview();
  const suggestEffectsMutation = useSuggestEffects();
  const translateMutation = useTranslate();
  const thumbnailMutation = useCreateThumbnail();

  // Tone transform modal
  const [toneModalOpen, setToneModalOpen] = useState(false);
  const [tonePlatform, setTonePlatform] = useState<string>('YOUTUBE');
  const [toneTone, setToneTone] = useState<string>('casual');

  // Content review modal
  const [reviewModalOpen, setReviewModalOpen] = useState(false);

  // Translation modal
  const [translateModalOpen, setTranslateModalOpen] = useState(false);
  const [translateLang, setTranslateLang] = useState<string>('en');

  // Thumbnail modal
  const [thumbnailModalOpen, setThumbnailModalOpen] = useState(false);
  const [thumbnailStyle, setThumbnailStyle] = useState<string>('modern');
  const [thumbnailRatio, setThumbnailRatio] = useState<string>('16:9');
  const [thumbnailJobId, setThumbnailJobId] = useState<string | null>(null);
  const thumbnailJobStatus = useJobStatus(thumbnailJobId);

  useEffect(() => {
    if (content) {
      form.setFieldsValue({
        title: content.title,
        body: content.body,
        platforms: content.platforms,
        media_urls: content.media_urls || [],
        scheduled_at: content.scheduled_at ? dayjs(content.scheduled_at) : null,
      });
    }
  }, [content, form]);

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Spin size="large" /></div>;
  }

  if (!content) {
    return <div className="p-6"><Title level={4}>콘텐츠를 찾을 수 없습니다</Title></div>;
  }

  /** Build update data from form values. */
  const buildUpdateData = (values: Record<string, unknown>) => {
    const data: Record<string, unknown> = {
      title: values.title as string,
      body: values.body as string | undefined,
      platforms: (values.platforms as string[]) || [],
      media_urls: (values.media_urls as string[]) || [],
    };
    const hashtags = values.hashtags as string | undefined;
    if (hashtags) {
      data.hashtags = hashtags.split(/\s+/).filter(Boolean);
    }
    if (values.scheduled_at) {
      data.scheduled_at = (values.scheduled_at as { toISOString: () => string }).toISOString();
    } else {
      data.scheduled_at = null;
    }
    return data;
  };

  /** Save draft without finalizing. */
  const handleSaveDraft = async () => {
    if (!id) return;
    try {
      const values = form.getFieldsValue(true);
      await saveDraftMutation.mutateAsync({ id, data: buildUpdateData(values) });
      message.success(CONTENT_MESSAGES.SAVE_DRAFT_SUCCESS);
    } catch {
      message.error(CONTENT_MESSAGES.SAVE_DRAFT_ERROR);
    }
  };

  /** Save and request review. */
  const handleRequestReview = async () => {
    if (!id) return;
    try {
      const values = await form.validateFields();
      await updateMutation.mutateAsync({ id, data: buildUpdateData(values) });
      await reviewMutation.mutateAsync(id);
      message.success(CONTENT_MESSAGES.REQUEST_REVIEW_SUCCESS);
      navigate(`/contents/${id}`);
    } catch {
      message.error(CONTENT_MESSAGES.REQUEST_REVIEW_ERROR);
    }
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    if (!id) return;
    try {
      await updateMutation.mutateAsync({ id, data: buildUpdateData(values) });
      message.success(CONTENT_MESSAGES.UPDATE_SUCCESS);
      navigate(`/contents/${id}`);
    } catch {
      message.error(CONTENT_MESSAGES.UPDATE_ERROR);
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

  const getSelectedPlatform = (): string | undefined => {
    const platforms = form.getFieldValue('platforms') as string[] | undefined;
    return platforms?.[0];
  };

  const handleGenerateTitle = () => {
    const contentText = getContentText();
    if (!contentText) return;
    titleMutation.mutate({ content_text: contentText, platform: getSelectedPlatform(), count: 3 });
  };

  const handleGenerateDescription = () => {
    const contentText = getContentText();
    if (!contentText) return;
    descriptionMutation.mutate({ content_text: contentText, platform: getSelectedPlatform(), count: 2 });
  };

  const handleGenerateHashtags = () => {
    const contentText = getContentText();
    if (!contentText) return;
    hashtagMutation.mutate({ content_text: contentText, platform: getSelectedPlatform(), count: 5 });
  };

  const handleToneTransform = () => {
    const contentText = getContentText();
    if (!contentText) return;
    setToneModalOpen(true);
    toneTransformMutation.mutate(
      { content_text: contentText, target_platform: tonePlatform, target_tone: toneTone, count: 2 },
      { onError: () => message.error('AI 톤 변환에 실패했습니다') },
    );
  };

  const handleToneTransformRerun = () => {
    const contentText = getContentText();
    if (!contentText) return;
    toneTransformMutation.mutate(
      { content_text: contentText, target_platform: tonePlatform, target_tone: toneTone, count: 2 },
      { onError: () => message.error('AI 톤 변환에 실패했습니다') },
    );
  };

  const handleContentReview = () => {
    const contentText = getContentText();
    if (!contentText) return;
    setReviewModalOpen(true);
    contentReviewMutation.mutate(
      { content_text: contentText, check_spelling: true, check_sensitivity: true, check_bias: true },
      {
        onSuccess: () => setReviewModalOpen(false),
        onError: () => message.error('AI 검수에 실패했습니다'),
      },
    );
  };

  const handleSuggestEffects = () => {
    const contentText = getContentText();
    if (!contentText) return;
    suggestEffectsMutation.mutate(
      { content_text: contentText, content_type: 'video', count: 5 },
      { onError: () => message.error('AI 효과음 추천에 실패했습니다') },
    );
  };

  const handleTranslate = () => {
    const contentText = getContentText();
    if (!contentText) return;
    setTranslateModalOpen(true);
  };

  const handleTranslateRun = () => {
    const body = form.getFieldValue('body') as string | undefined;
    if (!body || body.trim().length < 10) {
      message.warning('AI 번역을 받으려면 본문을 10자 이상 입력하세요.');
      return;
    }
    translateMutation.mutate(
      { content_text: body.trim(), target_language: translateLang },
      { onError: () => message.error('AI 번역에 실패했습니다') },
    );
  };

  const handleGenerateThumbnail = () => {
    const contentText = getContentText();
    if (!contentText) return;
    setThumbnailModalOpen(true);
  };

  const handleThumbnailRun = () => {
    const body = form.getFieldValue('body') as string | undefined;
    if (!body || body.trim().length < 10) {
      message.warning('AI 썸네일 생성을 위해 본문을 10자 이상 입력하세요.');
      return;
    }
    thumbnailMutation.mutate(
      { content_text: body.trim(), style: thumbnailStyle, count: 3, aspect_ratio: thumbnailRatio },
      {
        onSuccess: (data) => setThumbnailJobId(data.job_id),
        onError: () => message.error('AI 썸네일 생성 요청에 실패했습니다'),
      },
    );
  };

  // G4: Preview values
  const previewTitle = watchedTitle || '제목을 입력하세요';
  const previewBody = watchedBody || '';
  const previewHashtags = watchedHashtags || '#해시태그';

  const canRequestReview = content.status === 'DRAFT' || content.status === 'REJECTED';

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/contents/${id}`)} />
          <Title level={4} className="!mb-0">콘텐츠 수정</Title>
        </div>
        <Space>
          {content.status === 'DRAFT' && (
            <Button onClick={handleSaveDraft} loading={saveDraftMutation.isPending}>
              임시 저장
            </Button>
          )}
          {canRequestReview && (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleRequestReview}
              loading={updateMutation.isPending || reviewMutation.isPending}
            >
              검토 요청
            </Button>
          )}
        </Space>
      </div>

      <Form form={form} layout="vertical" onFinish={handleSubmit}>
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
                  <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>저장</Button>
                  <Button onClick={() => navigate(`/contents/${id}`)}>취소</Button>
                </Space>
              </Form.Item>
            </Card>
          </Col>

          {/* Right: Preview + AI panels */}
          <Col xs={24} lg={8}>
            {/* Platform preview */}
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
                        <Typography.Text strong className="text-sm">{previewTitle}</Typography.Text>
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
                        <Typography.Text strong className="text-sm">{previewTitle}</Typography.Text>
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
              title={<Space><RobotOutlined /><span>AI 어시스턴트</span></Space>}
              size="small"
            >
              <Space direction="vertical" className="w-full" size={16}>
                <div>
                  <Button type="default" icon={<RobotOutlined />} onClick={handleGenerateTitle} loading={titleMutation.isPending} block>
                    제목 제안 받기
                  </Button>
                  <div className="mt-2">
                    <AiSuggestionPanel
                      title="AI 제목 제안"
                      suggestions={titleMutation.data?.suggestions ?? []}
                      loading={titleMutation.isPending}
                      onSelect={(c) => form.setFieldValue('title', c)}
                      error={titleMutation.data?.error}
                      model={titleMutation.data?.model}
                      processingTimeMs={titleMutation.data?.processing_time_ms}
                    />
                  </div>
                </div>

                <Divider className="!my-2" />

                <div>
                  <Button type="default" icon={<RobotOutlined />} onClick={handleGenerateDescription} loading={descriptionMutation.isPending} block>
                    설명문 제안 받기
                  </Button>
                  <div className="mt-2">
                    <AiSuggestionPanel
                      title="AI 설명문 제안"
                      suggestions={descriptionMutation.data?.suggestions ?? []}
                      loading={descriptionMutation.isPending}
                      onSelect={(c) => {
                        const currentBody = (form.getFieldValue('body') as string) || '';
                        form.setFieldValue('body', currentBody ? `${currentBody}\n\n${c}` : c);
                      }}
                      error={descriptionMutation.data?.error}
                      model={descriptionMutation.data?.model}
                      processingTimeMs={descriptionMutation.data?.processing_time_ms}
                    />
                  </div>
                </div>

                <Divider className="!my-2" />

                <div>
                  <Button type="default" icon={<RobotOutlined />} onClick={handleGenerateHashtags} loading={hashtagMutation.isPending} block>
                    해시태그 제안 받기
                  </Button>
                  <div className="mt-2">
                    <AiSuggestionPanel
                      title="AI 해시태그 제안"
                      suggestions={hashtagMutation.data?.suggestions ?? []}
                      loading={hashtagMutation.isPending}
                      onSelect={(c) => {
                        const currentHashtags = (form.getFieldValue('hashtags') as string) || '';
                        const hashtag = c.startsWith('#') ? c : `#${c}`;
                        form.setFieldValue('hashtags', currentHashtags ? `${currentHashtags} ${hashtag}` : hashtag);
                      }}
                      error={hashtagMutation.data?.error}
                      model={hashtagMutation.data?.model}
                      processingTimeMs={hashtagMutation.data?.processing_time_ms}
                    />
                  </div>
                </div>

                <Divider className="!my-2" />

                <div>
                  <Button type="default" icon={<SwapOutlined />} onClick={handleToneTransform} loading={toneTransformMutation.isPending} block>
                    AI 톤 변환
                  </Button>
                </div>

                <Divider className="!my-2" />

                <div>
                  <Button type="default" icon={<CheckCircleOutlined />} onClick={handleContentReview} loading={contentReviewMutation.isPending} block>
                    AI 콘텐츠 검수
                  </Button>
                </div>

                <Divider className="!my-2" />

                <div>
                  <Button type="default" icon={<TranslationOutlined />} onClick={handleTranslate} loading={translateMutation.isPending} block>
                    AI 번역
                  </Button>
                </div>

                <Divider className="!my-2" />

                <div>
                  <Button type="default" icon={<PictureOutlined />} onClick={handleGenerateThumbnail} loading={thumbnailMutation.isPending} block>
                    AI 썸네일 생성
                  </Button>
                </div>
              </Space>
            </Card>

            {/* AI Review inline results */}
            <Card
              title={<Space><CheckCircleOutlined /><span>AI 검수 결과</span></Space>}
              size="small"
              className="mt-4"
            >
              {contentReviewMutation.isPending && (
                <div className="flex items-center justify-center py-4">
                  <Space><Spin size="small" /><Typography.Text type="secondary">AI가 콘텐츠를 검수하고 있습니다...</Typography.Text></Space>
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
                              <Tag color={issue.severity === 'HIGH' ? 'red' : issue.severity === 'MEDIUM' ? 'orange' : 'default'}>
                                {issue.severity}
                              </Tag>
                              <Typography.Text className="text-xs">{issue.issue}</Typography.Text>
                            </Space>
                            {issue.suggestion && (
                              <div className="mt-1 pl-1">
                                <Typography.Text type="secondary" className="text-xs">제안: {issue.suggestion}</Typography.Text>
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
              title={<Space><VideoCameraOutlined /><span>영상 콘텐츠 추가 기능</span></Space>}
              size="small"
              className="mt-4"
            >
              <Space direction="vertical" className="w-full" size={8}>
                <Button
                  type="default"
                  icon={<RobotOutlined />}
                  onClick={handleSuggestEffects}
                  loading={suggestEffectsMutation.isPending}
                  block
                  size="small"
                >
                  효과음/이모지 추천
                </Button>
                <div className="mt-1">
                  <AiSuggestionPanel
                    title="AI 효과음/이모지 추천"
                    suggestions={suggestEffectsMutation.data?.suggestions ?? []}
                    loading={suggestEffectsMutation.isPending}
                    onSelect={(c) => {
                      const currentBody = (form.getFieldValue('body') as string) || '';
                      form.setFieldValue('body', currentBody ? `${currentBody}\n\n${c}` : c);
                      message.success('효과음 추천이 본문에 추가되었습니다');
                    }}
                    error={suggestEffectsMutation.data?.error}
                    model={suggestEffectsMutation.data?.model}
                    processingTimeMs={suggestEffectsMutation.data?.processing_time_ms}
                  />
                </div>
              </Space>
            </Card>
          </Col>
        </Row>
      </Form>

      {/* Tone Transform Modal */}
      <Modal
        title={<Space><SwapOutlined /><span>AI 톤 변환</span></Space>}
        open={toneModalOpen}
        onCancel={() => { setToneModalOpen(false); toneTransformMutation.reset(); }}
        footer={null}
        width={640}
      >
        <div className="mb-4 flex items-center gap-3">
          <Select value={tonePlatform} onChange={setTonePlatform} style={{ width: 160 }} options={PLATFORM_OPTIONS} />
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
          <Button type="primary" onClick={handleToneTransformRerun} loading={toneTransformMutation.isPending}>변환하기</Button>
        </div>
        {toneTransformMutation.isPending && (
          <div className="flex items-center justify-center py-8">
            <Space><Spin size="small" /><Typography.Text type="secondary">AI가 콘텐츠를 변환하고 있습니다...</Typography.Text></Space>
          </div>
        )}
        {toneTransformMutation.data?.error && (
          <Alert type="warning" message={toneTransformMutation.data.error} showIcon className="mb-4" />
        )}
        {toneTransformMutation.data?.suggestions && toneTransformMutation.data.suggestions.length > 0 && (
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Typography.Text strong>변환 결과</Typography.Text>
              {toneTransformMutation.data.model && <Tag color="blue">{toneTransformMutation.data.model}</Tag>}
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
                    description={<Progress percent={Math.round(item.score * 100)} size="small" className="!mb-0 w-24" format={(p) => `${p}%`} />}
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

      {/* Content Review Modal */}
      <Modal
        title={<Space><CheckCircleOutlined /><span>AI 콘텐츠 검수</span></Space>}
        open={reviewModalOpen}
        onCancel={() => setReviewModalOpen(false)}
        footer={null}
        width={400}
      >
        <div className="flex items-center justify-center py-8">
          <Space><Spin size="small" /><Typography.Text type="secondary">AI가 콘텐츠를 검수하고 있습니다...</Typography.Text></Space>
        </div>
        <Typography.Text type="secondary" className="block text-center text-xs">
          완료되면 결과가 우측 패널에 표시됩니다.
        </Typography.Text>
      </Modal>

      {/* Translation Modal (F22) */}
      <Modal
        title={<Space><TranslationOutlined /><span>AI 다국어 번역</span></Space>}
        open={translateModalOpen}
        onCancel={() => { setTranslateModalOpen(false); translateMutation.reset(); }}
        footer={null}
        width={640}
      >
        <div className="mb-4 flex items-center gap-3">
          <Select
            value={translateLang}
            onChange={setTranslateLang}
            style={{ width: 160 }}
            options={[
              { value: 'en', label: '영어 (English)' },
              { value: 'zh', label: '중국어 (中文)' },
              { value: 'ja', label: '일본어 (日本語)' },
              { value: 'vi', label: '베트남어 (Tiếng Việt)' },
            ]}
          />
          <Button type="primary" onClick={handleTranslateRun} loading={translateMutation.isPending}>
            번역하기
          </Button>
        </div>

        {translateMutation.isPending && (
          <div className="flex items-center justify-center py-8">
            <Space><Spin size="small" /><Typography.Text type="secondary">AI가 콘텐츠를 번역하고 있습니다...</Typography.Text></Space>
          </div>
        )}

        {translateMutation.data?.error && (
          <Alert type="warning" message={translateMutation.data.error} showIcon className="mb-4" />
        )}

        {translateMutation.data && !translateMutation.data.error && !translateMutation.isPending && (
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Tag color="blue">{translateMutation.data.model}</Tag>
              <Tag>{translateMutation.data.target_language.toUpperCase()}</Tag>
              <Typography.Text type="secondary" className="text-xs">
                신뢰도: {Math.round(translateMutation.data.confidence * 100)}%
              </Typography.Text>
            </div>
            <Input.TextArea
              value={translateMutation.data.translated_text}
              rows={6}
              readOnly
              className="mb-2"
            />
            {translateMutation.data.notes && (
              <Alert type="info" message={translateMutation.data.notes} showIcon className="mb-2" />
            )}
            <Button
              type="primary"
              size="small"
              onClick={() => {
                form.setFieldValue('body', translateMutation.data?.translated_text ?? '');
                message.success('번역 결과가 본문에 적용되었습니다');
                setTranslateModalOpen(false);
              }}
            >
              본문에 적용
            </Button>
            <Typography.Text type="secondary" className="mt-2 block text-xs">
              AI가 생성한 번역입니다. 최종 결정은 사용자가 합니다.
            </Typography.Text>
          </div>
        )}
      </Modal>

      {/* Thumbnail Generation Modal (F16) */}
      <Modal
        title={<Space><PictureOutlined /><span>AI 썸네일 생성</span></Space>}
        open={thumbnailModalOpen}
        onCancel={() => { setThumbnailModalOpen(false); setThumbnailJobId(null); thumbnailMutation.reset(); }}
        footer={null}
        width={720}
      >
        <div className="mb-4 flex items-center gap-3">
          <Select
            value={thumbnailStyle}
            onChange={setThumbnailStyle}
            style={{ width: 140 }}
            options={[
              { value: 'modern', label: '모던' },
              { value: 'classic', label: '클래식' },
              { value: 'minimalist', label: '미니멀' },
              { value: 'bold', label: '볼드' },
            ]}
          />
          <Select
            value={thumbnailRatio}
            onChange={setThumbnailRatio}
            style={{ width: 120 }}
            options={[
              { value: '16:9', label: '16:9' },
              { value: '1:1', label: '1:1' },
              { value: '4:3', label: '4:3' },
              { value: '9:16', label: '9:16' },
            ]}
          />
          <Button type="primary" onClick={handleThumbnailRun} loading={thumbnailMutation.isPending}>
            생성하기
          </Button>
        </div>

        {thumbnailJobId && thumbnailJobStatus.data && (
          <div className="mb-4">
            {(thumbnailJobStatus.data.status === 'PENDING' || thumbnailJobStatus.data.status === 'PROCESSING') && (
              <div className="py-6 text-center">
                <Spin size="large" />
                <div className="mt-3">
                  <Progress percent={thumbnailJobStatus.data.progress} status="active" />
                  <Typography.Text type="secondary">AI가 썸네일을 생성하고 있습니다...</Typography.Text>
                </div>
              </div>
            )}

            {thumbnailJobStatus.data.status === 'FAILED' && (
              <Alert
                type="error"
                message="썸네일 생성 실패"
                description={thumbnailJobStatus.data.error_message || '다시 시도해주세요.'}
                showIcon
              />
            )}

            {thumbnailJobStatus.data.status === 'COMPLETED' && thumbnailJobStatus.data.result && (
              <div>
                <Typography.Text strong className="mb-3 block">썸네일 후보</Typography.Text>
                <Row gutter={[12, 12]}>
                  {(
                    (thumbnailJobStatus.data.result as { candidates?: Array<Record<string, unknown>> })
                      .candidates ?? []
                  ).map((candidate: Record<string, unknown>, idx: number) => (
                    <Col span={8} key={idx}>
                      <Card
                        size="small"
                        hoverable
                        className="text-center"
                        style={{
                          background: Array.isArray(candidate.colors) && candidate.colors.length > 0
                            ? `linear-gradient(135deg, ${(candidate.colors as string[])[0]}, ${(candidate.colors as string[])[(candidate.colors as string[]).length - 1]})`
                            : '#f5f5f5',
                          minHeight: 140,
                        }}
                      >
                        <div className="flex flex-col items-center justify-center" style={{ minHeight: 80 }}>
                          <Typography.Text
                            strong
                            className="text-sm"
                            style={{ color: '#fff', textShadow: '1px 1px 2px rgba(0,0,0,0.5)' }}
                          >
                            {(candidate.text_overlay as string) || '텍스트'}
                          </Typography.Text>
                        </div>
                        <div className="mt-2 rounded bg-white/80 p-1">
                          <Typography.Text className="text-xs">
                            {(candidate.layout as string) || 'center-text'}
                          </Typography.Text>
                          {typeof candidate.score === 'number' && (
                            <Progress
                              percent={Math.round(candidate.score * 100)}
                              size="small"
                              className="!mb-0"
                            />
                          )}
                        </div>
                      </Card>
                    </Col>
                  ))}
                </Row>
                <Typography.Text type="secondary" className="mt-3 block text-xs">
                  AI가 제안한 썸네일 디자인입니다. 실제 이미지 생성은 프로덕션 환경에서 지원됩니다.
                </Typography.Text>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
