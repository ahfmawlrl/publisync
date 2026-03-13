import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  PictureOutlined,
  RobotOutlined,
  SwapOutlined,
  TranslationOutlined,
} from '@ant-design/icons';
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
  Modal,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';

import AiSuggestionPanel from '@/features/ai/components/AiSuggestionPanel';
import {
  useContentReview,
  useGenerateDescription,
  useGenerateHashtags,
  useGenerateTitle,
  useToneTransform,
  useTranslate,
} from '@/features/ai/hooks/useAi';
import { useCreateThumbnail, useJobStatus } from '@/features/ai/hooks/useAiJobs';
import apiClient from '@/shared/api/client';
import type { PaginatedResponse } from '@/shared/api/types';
import { CONTENT_MESSAGES } from '@/shared/constants/messages';
import SourceMediaSection from '../components/SourceMediaSection';
import VariantEditor from '../components/VariantEditor';
import PlatformPreview from '../components/PlatformPreview';
import {
  useContent,
  useCreateContent,
  useRequestReview,
  useSaveDraft,
  useUpdateContent,
} from '../hooks/useContents';
import type { ContentCreateData, ContentUpdateData, VariantCreateData } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const PLATFORM_OPTIONS = [
  { value: 'YOUTUBE', label: 'YouTube' },
  { value: 'INSTAGRAM', label: 'Instagram' },
  { value: 'FACEBOOK', label: 'Facebook' },
  { value: 'X', label: 'X (Twitter)' },
  { value: 'NAVER_BLOG', label: '네이버 블로그' },
];

interface VariantState {
  title: string;
  body: string;
  hashtags: string[];
  channel_id: string | null;
}

export default function ContentEditorPage() {
  const { id } = useParams<{ id: string }>();
  const isEditMode = !!id;
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  // Mutations
  const createMutation = useCreateContent();
  const updateMutation = useUpdateContent();
  const saveDraftMutation = useSaveDraft();
  const reviewMutation = useRequestReview();

  // Load content for edit mode
  const { data: content, isLoading } = useContent(isEditMode ? id : null);

  // Publish mode: false = 전체 동일 게시, true = 플랫폼별 커스터마이즈
  const [customizeMode, setCustomizeMode] = useState(false);

  // Per-platform variant state (only used in customize mode)
  const [variantStates, setVariantStates] = useState<Record<string, VariantState>>({});

  // Watched form fields for reactive preview
  const watchedTitle = Form.useWatch('title', form);
  const watchedBody = Form.useWatch('body', form);
  const watchedHashtags = Form.useWatch('hashtags', form);
  const watchedPlatforms = Form.useWatch('platforms', form) as string[] | undefined;

  // Fetch channels
  interface ChannelOption { id: string; name: string; platform: string; status: string }
  const { data: channelsData } = useQuery({
    queryKey: ['channels', 'all'],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ChannelOption>>('/channels', { params: { limit: 100 } });
      return res.data.data;
    },
  });

  // Filter channels by platform and status
  const activeChannels = useMemo(() => {
    if (!channelsData) return [];
    return channelsData.filter((ch) => ch.status === 'ACTIVE');
  }, [channelsData]);

  const channelOptionsByPlatform = useMemo(() => {
    const map: Record<string, { value: string; label: string }[]> = {};
    for (const ch of activeChannels) {
      if (!map[ch.platform]) map[ch.platform] = [];
      map[ch.platform].push({ value: ch.id, label: `${ch.name} (${ch.platform})` });
    }
    return map;
  }, [activeChannels]);

  // Uniform mode: all active channels for selected platforms
  const uniformChannelOptions = useMemo(() => {
    if (!watchedPlatforms?.length) return [];
    return activeChannels
      .filter((ch) => watchedPlatforms.includes(ch.platform))
      .map((ch) => ({ value: ch.id, label: `${ch.name} (${ch.platform})` }));
  }, [activeChannels, watchedPlatforms]);

  // AI mutations
  const titleMutation = useGenerateTitle();
  const descriptionMutation = useGenerateDescription();
  const hashtagMutation = useGenerateHashtags();
  const toneTransformMutation = useToneTransform();
  const contentReviewMutation = useContentReview();
  const translateMutation = useTranslate();
  const thumbnailMutation = useCreateThumbnail();

  // Modal states
  const [toneModalOpen, setToneModalOpen] = useState(false);
  const [tonePlatform, setTonePlatform] = useState('YOUTUBE');
  const [toneTone, setToneTone] = useState('casual');
  const [translateModalOpen, setTranslateModalOpen] = useState(false);
  const [translateLang, setTranslateLang] = useState('en');
  const [thumbnailModalOpen, setThumbnailModalOpen] = useState(false);
  const [thumbnailStyle, setThumbnailStyle] = useState('modern');
  const [thumbnailRatio, setThumbnailRatio] = useState('16:9');
  const [thumbnailJobId, setThumbnailJobId] = useState<string | null>(null);
  const thumbnailJobStatus = useJobStatus(thumbnailJobId);
  const [reviewConfirmOpen, setReviewConfirmOpen] = useState(false);

  // Populate form in edit mode
  useEffect(() => {
    if (!content) return;
    form.setFieldsValue({
      title: content.title,
      body: content.body,
      platforms: content.platforms,
      channel_ids: content.channel_ids,
      hashtags: content.hashtags,
      media_urls: content.media_urls,
      scheduled_at: content.scheduled_at ? dayjs(content.scheduled_at) : undefined,
    });

    // If content has variants, switch to customize mode
    if (content.variants && content.variants.length > 0) {
      setCustomizeMode(true);
      const states: Record<string, VariantState> = {};
      for (const v of content.variants) {
        states[v.platform] = {
          title: v.title || '',
          body: v.body || '',
          hashtags: v.hashtags || [],
          channel_id: v.channel_id,
        };
      }
      setVariantStates(states);
    }
  }, [content, form]);

  // Variant state update handler
  const handleVariantChange = useCallback(
    (platform: string, field: 'title' | 'body' | 'hashtags' | 'channel_id', value: unknown) => {
      setVariantStates((prev) => ({
        ...prev,
        [platform]: {
          ...prev[platform],
          title: prev[platform]?.title || '',
          body: prev[platform]?.body || '',
          hashtags: prev[platform]?.hashtags || [],
          channel_id: prev[platform]?.channel_id || null,
          [field]: value,
        },
      }));
    },
    [],
  );

  // ── Build submit data ──

  const buildCreateData = (values: Record<string, unknown>): ContentCreateData => {
    const rawUrls = (values.media_urls as string[]) || [];
    const persistableUrls = rawUrls.filter((url) => !url.startsWith('blob:'));
    if (persistableUrls.length < rawUrls.length) {
      message.warning('스토리지에 업로드되지 않은 미디어는 저장에서 제외됩니다.');
    }

    const data: ContentCreateData = {
      title: values.title as string,
      body: values.body as string | undefined,
      platforms: (values.platforms as string[]) || [],
      channel_ids: (values.channel_ids as string[]) || [],
      media_urls: persistableUrls,
    };

    const hashtags = values.hashtags as string[] | undefined;
    if (hashtags && hashtags.length > 0) data.hashtags = hashtags;
    if (values.scheduled_at) {
      data.scheduled_at = (values.scheduled_at as { toISOString: () => string }).toISOString();
    }
    if (titleMutation.data || descriptionMutation.data || hashtagMutation.data) {
      data.ai_generated = true;
    }

    // v2.0: variant mode
    if (customizeMode && watchedPlatforms && watchedPlatforms.length > 0) {
      const variants: VariantCreateData[] = [];
      for (const p of watchedPlatforms) {
        const vs = variantStates[p];
        if (vs) {
          variants.push({
            platform: p,
            channel_id: vs.channel_id || undefined,
            title: vs.title || undefined,
            body: vs.body || undefined,
            hashtags: vs.hashtags.length > 0 ? vs.hashtags : undefined,
          });
        } else {
          variants.push({ platform: p });
        }
      }
      data.variants = variants;
    } else {
      data.uniform_publish = true;
    }

    return data;
  };

  const buildUpdateData = (values: Record<string, unknown>): ContentUpdateData => {
    const rawUrls = (values.media_urls as string[]) || [];
    const persistableUrls = rawUrls.filter((url) => !url.startsWith('blob:'));
    if (persistableUrls.length < rawUrls.length) {
      message.warning('스토리지에 업로드되지 않은 미디어는 저장에서 제외됩니다.');
    }

    const data: ContentUpdateData = {
      title: values.title as string,
      body: values.body as string | undefined,
      platforms: (values.platforms as string[]) || [],
      channel_ids: (values.channel_ids as string[]) || [],
      media_urls: persistableUrls,
    };

    const hashtags = values.hashtags as string[] | undefined;
    if (hashtags && hashtags.length > 0) data.hashtags = hashtags;
    if (values.scheduled_at) {
      data.scheduled_at = (values.scheduled_at as { toISOString: () => string }).toISOString();
    } else {
      data.scheduled_at = null;
    }

    return data;
  };

  // ── Actions ──

  const handleSaveDraft = async () => {
    try { await form.validateFields(['title']); } catch { return; }
    try {
      if (isEditMode) {
        const data = buildUpdateData(form.getFieldsValue(true));
        await saveDraftMutation.mutateAsync({ id, data });
      } else {
        const data = buildCreateData(form.getFieldsValue(true));
        const result = await createMutation.mutateAsync(data);
        navigate(`/contents/${result.id}`, { replace: true });
      }
      message.success(CONTENT_MESSAGES.SAVE_DRAFT_SUCCESS);
    } catch {
      message.error(CONTENT_MESSAGES.SAVE_DRAFT_ERROR);
    }
  };

  const handleRequestReview = async () => {
    try {
      const values = await form.validateFields();
      if (isEditMode) {
        const data = buildUpdateData(values);
        await updateMutation.mutateAsync({ id, data });
        await reviewMutation.mutateAsync(id);
      } else {
        const data = buildCreateData(values);
        const result = await createMutation.mutateAsync(data);
        await reviewMutation.mutateAsync(result.id);
        navigate(`/contents/${result.id}`, { replace: true });
      }
      message.success(CONTENT_MESSAGES.REQUEST_REVIEW_SUCCESS);
      setReviewConfirmOpen(false);
      if (isEditMode) navigate(`/contents/${id}`);
    } catch {
      message.error(CONTENT_MESSAGES.REQUEST_REVIEW_ERROR);
    }
  };

  // ── AI helpers ──

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

  // Preview values
  const previewTitle = watchedTitle || '제목을 입력하세요';
  const previewBody = watchedBody || '';
  const previewHashtags = Array.isArray(watchedHashtags) && watchedHashtags.length > 0
    ? watchedHashtags
    : [];

  const isSaving = createMutation.isPending || updateMutation.isPending || saveDraftMutation.isPending;

  if (isEditMode && isLoading) {
    return <div className="flex h-64 items-center justify-center"><Spin size="large" /></div>;
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/contents')} />
          <Title level={4} className="!mb-0">
            {isEditMode ? '콘텐츠 편집' : '새 콘텐츠 작성'}
          </Title>
          {isEditMode && content && (
            <Tag color="blue">{content.status}</Tag>
          )}
        </div>
        <Space>
          <Button onClick={handleSaveDraft} loading={isSaving}>
            임시 저장
          </Button>
          <Button
            type="primary"
            onClick={() => setReviewConfirmOpen(true)}
            loading={isSaving || reviewMutation.isPending}
          >
            검수 요청
          </Button>
        </Space>
      </div>

      <Form form={form} layout="vertical" initialValues={{ platforms: [], channel_ids: [] }}>
        {/* ── 상단: 공통 정보 ── */}
        <Card className="mb-4">
          <div className="mb-4 flex items-center gap-4">
            <Form.Item name="platforms" className="!mb-0">
              <Checkbox.Group options={PLATFORM_OPTIONS} />
            </Form.Item>
          </div>

          {/* Publish mode toggle */}
          <div className="mb-4 flex items-center gap-3">
            <Text>게시 모드:</Text>
            <Switch
              checked={customizeMode}
              onChange={setCustomizeMode}
              checkedChildren="플랫폼별 커스터마이즈"
              unCheckedChildren="전체 동일 게시"
            />
          </div>

          {/* Uniform mode: channel multi-select */}
          {!customizeMode && (
            <Form.Item name="channel_ids" label="게시 채널" className="mb-4">
              {uniformChannelOptions.length > 0 ? (
                <Select
                  mode="multiple"
                  placeholder="게시 채널 선택"
                  options={uniformChannelOptions}
                  allowClear
                />
              ) : watchedPlatforms && watchedPlatforms.length > 0 ? (
                <Text type="secondary" className="text-xs">
                  선택한 플랫폼에 연결된 채널이 없습니다. 채널 관리에서 연동하세요.
                </Text>
              ) : (
                <Text type="secondary" className="text-xs">
                  플랫폼을 먼저 선택하세요.
                </Text>
              )}
            </Form.Item>
          )}

          <Row gutter={24}>
            <Col xs={24} lg={16}>
              <Form.Item name="media_urls" label="미디어 소재">
                <SourceMediaSection maxFiles={10} />
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
                    onClick={() => {
                      const text = getContentText();
                      if (text) titleMutation.mutate({ content_text: text, platform: getSelectedPlatform(), count: 3 });
                    }}
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
                    onClick={() => {
                      const text = getContentText();
                      if (text) hashtagMutation.mutate({ content_text: text, platform: getSelectedPlatform(), count: 5 });
                    }}
                    loading={hashtagMutation.isPending}
                    className="mt-1 !p-0"
                  >
                    AI 해시태그 추천
                  </Button>
                }
              >
                <Select mode="tags" placeholder="#서울시 #정책브리핑" tokenSeparators={[' ', ',']} />
              </Form.Item>

              <Form.Item name="scheduled_at" label="예약 게시일시">
                <DatePicker showTime format="YYYY-MM-DD HH:mm" placeholder="예약 게시 (선택)" className="w-full" />
              </Form.Item>
            </Col>

            {/* Right: AI panels + preview (uniform mode only) */}
            <Col xs={24} lg={8}>
              {!customizeMode && (
                <Card title="플랫폼별 미리보기" size="small" className="mb-4">
                  <div className="grid grid-cols-1 gap-3">
                    {(watchedPlatforms || []).map((p: string) => (
                      <PlatformPreview
                        key={p}
                        platform={p}
                        title={previewTitle}
                        body={previewBody}
                        hashtags={previewHashtags}
                      />
                    ))}
                    {(!watchedPlatforms || watchedPlatforms.length === 0) && (
                      <Text type="secondary" className="text-xs">플랫폼을 선택하면 미리보기가 표시됩니다.</Text>
                    )}
                  </div>
                </Card>
              )}

              {/* AI Assistant */}
              <Card
                title={<Space><RobotOutlined /><span>AI 어시스턴트</span></Space>}
                size="small"
              >
                <Space direction="vertical" className="w-full" size={8}>
                  <Button type="default" icon={<RobotOutlined />} block
                    onClick={() => { const t = getContentText(); if (t) titleMutation.mutate({ content_text: t, platform: getSelectedPlatform(), count: 3 }); }}
                    loading={titleMutation.isPending}
                  >제목 제안 받기</Button>
                  <AiSuggestionPanel
                    title="AI 제목 제안"
                    suggestions={titleMutation.data?.suggestions ?? []}
                    loading={titleMutation.isPending}
                    onSelect={(c) => form.setFieldValue('title', c)}
                    error={titleMutation.data?.error}
                    model={titleMutation.data?.model}
                    processingTimeMs={titleMutation.data?.processing_time_ms}
                  />

                  <Divider className="!my-1" />

                  <Button type="default" icon={<RobotOutlined />} block
                    onClick={() => { const t = getContentText(); if (t) descriptionMutation.mutate({ content_text: t, platform: getSelectedPlatform(), count: 2 }); }}
                    loading={descriptionMutation.isPending}
                  >설명문 제안 받기</Button>
                  <AiSuggestionPanel
                    title="AI 설명문 제안"
                    suggestions={descriptionMutation.data?.suggestions ?? []}
                    loading={descriptionMutation.isPending}
                    onSelect={(c) => {
                      const cur = (form.getFieldValue('body') as string) || '';
                      form.setFieldValue('body', cur ? `${cur}\n\n${c}` : c);
                    }}
                    error={descriptionMutation.data?.error}
                    model={descriptionMutation.data?.model}
                    processingTimeMs={descriptionMutation.data?.processing_time_ms}
                  />

                  <Divider className="!my-1" />

                  <Button type="default" icon={<SwapOutlined />} block
                    onClick={() => { if (getContentText()) setToneModalOpen(true); }}
                    loading={toneTransformMutation.isPending}
                  >AI 톤 변환</Button>

                  <Button type="default" icon={<CheckCircleOutlined />} block
                    onClick={() => {
                      const t = getContentText();
                      if (t) contentReviewMutation.mutate({ content_text: t, check_spelling: true, check_sensitivity: true, check_bias: true });
                    }}
                    loading={contentReviewMutation.isPending}
                  >AI 콘텐츠 검수</Button>

                  <Button type="default" icon={<TranslationOutlined />} block
                    onClick={() => { if (getContentText()) setTranslateModalOpen(true); }}
                    loading={translateMutation.isPending}
                  >AI 번역</Button>

                  <Button type="default" icon={<PictureOutlined />} block
                    onClick={() => { if (getContentText()) setThumbnailModalOpen(true); }}
                    loading={thumbnailMutation.isPending}
                  >AI 썸네일 생성</Button>
                </Space>
              </Card>

              {/* AI Review Results */}
              {contentReviewMutation.data && !contentReviewMutation.isPending && (
                <Card
                  title={<Space><CheckCircleOutlined /><span>AI 검수 결과</span></Space>}
                  size="small"
                  className="mt-4"
                >
                  <Alert
                    type={contentReviewMutation.data.issues?.length > 0 ? 'warning' : 'success'}
                    message={contentReviewMutation.data.summary || '검수 완료'}
                    showIcon
                  />
                </Card>
              )}
            </Col>
          </Row>
        </Card>

        {/* ── 하단: 플랫폼 탭 (커스터마이즈 모드) ── */}
        {customizeMode && watchedPlatforms && watchedPlatforms.length > 0 && (
          <Card title="플랫폼별 커스터마이즈" className="mb-4">
            <Tabs
              items={watchedPlatforms.map((p: string) => {
                const opt = PLATFORM_OPTIONS.find((o) => o.value === p);
                const vs = variantStates[p] || { title: '', body: '', hashtags: [], channel_id: null };
                return {
                  key: p,
                  label: opt?.label || p,
                  children: (
                    <VariantEditor
                      platform={p}
                      title={vs.title}
                      body={vs.body}
                      hashtags={vs.hashtags}
                      channelId={vs.channel_id}
                      channelOptions={channelOptionsByPlatform[p] || []}
                      commonTitle={watchedTitle || ''}
                      commonBody={watchedBody || ''}
                      commonHashtags={Array.isArray(watchedHashtags) ? watchedHashtags : []}
                      onChange={(field, value) => handleVariantChange(p, field, value)}
                    />
                  ),
                };
              })}
            />
          </Card>
        )}

        {customizeMode && (!watchedPlatforms || watchedPlatforms.length === 0) && (
          <Alert
            type="info"
            message="플랫폼을 선택하면 플랫폼별 커스터마이즈 탭이 표시됩니다."
            className="mb-4"
          />
        )}
      </Form>

      {/* ── 검수 요청 확인 모달 ── */}
      <Modal
        title="검수 요청 확인"
        open={reviewConfirmOpen}
        onOk={handleRequestReview}
        onCancel={() => setReviewConfirmOpen(false)}
        okText="검수 요청"
        cancelText="취소"
        confirmLoading={isSaving || reviewMutation.isPending}
      >
        <div className="space-y-2">
          <Text>다음 콘텐츠를 검수 요청하시겠습니까?</Text>
          <div className="rounded bg-gray-50 p-3">
            <Text strong>{watchedTitle || '(제목 없음)'}</Text>
            <div className="mt-1 flex flex-wrap gap-1">
              {(watchedPlatforms || []).map((p: string) => {
                const opt = PLATFORM_OPTIONS.find((o) => o.value === p);
                return <Tag key={p}>{opt?.label || p}</Tag>;
              })}
            </div>
            {customizeMode && (
              <div className="mt-2 text-xs text-gray-500">
                {(watchedPlatforms || []).map((p: string) => {
                  const vs = variantStates[p];
                  const hasOverride = vs && (vs.title || vs.body);
                  return (
                    <div key={p}>
                      {PLATFORM_OPTIONS.find((o) => o.value === p)?.label || p}:{' '}
                      {hasOverride ? '커스터마이즈됨' : '공통 정보 사용'}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </Modal>

      {/* ── AI 톤 변환 모달 ── */}
      <Modal
        title="AI 톤 변환"
        open={toneModalOpen}
        onOk={() => {
          const body = form.getFieldValue('body') as string | undefined;
          if (body && body.trim().length >= 10) {
            toneTransformMutation.mutate(
              { content_text: body.trim(), target_platform: tonePlatform, target_tone: toneTone, count: 2 },
              { onError: () => message.error('AI 톤 변환에 실패했습니다') },
            );
          }
        }}
        onCancel={() => setToneModalOpen(false)}
        okText="변환하기"
        confirmLoading={toneTransformMutation.isPending}
      >
        <Space direction="vertical" className="w-full">
          <Select value={tonePlatform} onChange={setTonePlatform} options={PLATFORM_OPTIONS} className="w-full" />
          <Select
            value={toneTone}
            onChange={setToneTone}
            className="w-full"
            options={[
              { value: 'formal', label: '공식적' },
              { value: 'casual', label: '캐주얼' },
              { value: 'friendly', label: '친근한' },
              { value: 'professional', label: '전문적' },
            ]}
          />
        </Space>
        {toneTransformMutation.data && (
          <div className="mt-3">
            <AiSuggestionPanel
              title="톤 변환 결과"
              suggestions={toneTransformMutation.data.suggestions ?? []}
              loading={false}
              onSelect={(c) => { form.setFieldValue('body', c); setToneModalOpen(false); }}
              error={toneTransformMutation.data.error}
            />
          </div>
        )}
      </Modal>

      {/* ── AI 번역 모달 ── */}
      <Modal
        title="AI 번역"
        open={translateModalOpen}
        onOk={() => {
          const body = form.getFieldValue('body') as string | undefined;
          if (body && body.trim().length >= 10) {
            translateMutation.mutate(
              { content_text: body.trim(), target_language: translateLang },
              { onError: () => message.error('AI 번역에 실패했습니다') },
            );
          }
        }}
        onCancel={() => setTranslateModalOpen(false)}
        okText="번역하기"
        confirmLoading={translateMutation.isPending}
      >
        <Select
          value={translateLang}
          onChange={setTranslateLang}
          className="w-full"
          options={[
            { value: 'en', label: 'English' },
            { value: 'zh', label: '中文' },
            { value: 'ja', label: '日本語' },
            { value: 'vi', label: 'Tiếng Việt' },
          ]}
        />
        {translateMutation.data && (
          <div className="mt-3">
            <AiSuggestionPanel
              title="번역 결과"
              suggestions={translateMutation.data.suggestions ?? []}
              loading={false}
              onSelect={(c) => { form.setFieldValue('body', c); setTranslateModalOpen(false); }}
              error={translateMutation.data.error}
            />
          </div>
        )}
      </Modal>

      {/* ── AI 썸네일 모달 ── */}
      <Modal
        title="AI 썸네일 생성"
        open={thumbnailModalOpen}
        onOk={() => {
          const body = form.getFieldValue('body') as string | undefined;
          if (body && body.trim().length >= 10) {
            thumbnailMutation.mutate(
              { content_text: body.trim(), style: thumbnailStyle, count: 3, aspect_ratio: thumbnailRatio },
              {
                onSuccess: (data) => setThumbnailJobId(data.job_id),
                onError: () => message.error('AI 썸네일 생성 요청에 실패했습니다'),
              },
            );
          }
        }}
        onCancel={() => setThumbnailModalOpen(false)}
        okText="생성하기"
        confirmLoading={thumbnailMutation.isPending}
      >
        <Space direction="vertical" className="w-full">
          <Select
            value={thumbnailStyle}
            onChange={setThumbnailStyle}
            className="w-full"
            options={[
              { value: 'modern', label: '모던' },
              { value: 'minimalist', label: '미니멀' },
              { value: 'bold', label: '볼드' },
              { value: 'playful', label: '플레이풀' },
            ]}
          />
          <Select
            value={thumbnailRatio}
            onChange={setThumbnailRatio}
            className="w-full"
            options={[
              { value: '16:9', label: '16:9 (YouTube)' },
              { value: '1:1', label: '1:1 (Instagram)' },
              { value: '9:16', label: '9:16 (Shorts/Reels)' },
            ]}
          />
        </Space>
        {thumbnailJobStatus.data && (
          <div className="mt-3">
            <Alert
              type={thumbnailJobStatus.data.status === 'COMPLETED' ? 'success' : 'info'}
              message={`상태: ${thumbnailJobStatus.data.status}`}
            />
          </div>
        )}
      </Modal>
    </div>
  );
}
