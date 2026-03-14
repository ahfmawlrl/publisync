/**
 * ContentEditorPage — 영상 중심 콘텐츠 에디터 (v2.0 재설계).
 *
 * 레이아웃:
 *  - 헤더: 뒤로 / 제목 / [콘텐츠 정보] [플랫폼 설정] / [임시 저장] [검수 요청]
 *  - 메인: MediaMainArea (업로드→VideoPlayer/이미지 갤러리 자동 전환)
 *  - 도구 바: Segmented — 자막 | 효과음 | 이모지 | 숏폼 추출 | AI 어시스턴트
 *  - 활성 패널: 도구 바 선택에 따라 전환
 */

import {
  ArrowLeftOutlined,
  EditOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import {
  App,
  Button,
  Form,
  Modal,
  Segmented,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';

import {
  useGenerateDescription,
  useGenerateHashtags,
  useGenerateTitle,
} from '@/features/ai/hooks/useAi';
import { CONTENT_MESSAGES } from '@/shared/constants/messages';
import AiAssistantPanel from '../components/AiAssistantPanel';
import ContentInfoModal from '../components/ContentInfoModal';
import EffectsPanel, { type SoundEffectEntry } from '../components/EffectsPanel';
import EmojiPanel, { type EmojiOverlayEntry } from '../components/EmojiPanel';
import MediaMainArea, { type MediaMainAreaHandle } from '../components/MediaMainArea';
import PlatformSettingsModal from '../components/PlatformSettingsModal';
import ShortformEditorModal from '../components/ShortformEditorModal';
import SubtitleEditorModal from '../components/SubtitleEditorModal';
import {
  useContent,
  useCreateContent,
  useRequestReview,
  useSaveDraft,
  useUpdateContent,
} from '../hooks/useContents';
import type { ContentCreateData, ContentUpdateData, VariantCreateData } from '../types';

interface VariantState {
  title: string;
  body: string;
  hashtags: string[];
  channel_id: string | null;
}

/* ── sessionStorage 기반 폼 임시 보존 ── */
const DRAFT_STORAGE_KEY = 'publisync:content-editor-draft';

interface DraftSnapshot {
  title?: string;
  body?: string;
  platforms?: string[];
  channel_ids?: string[];
  hashtags?: string[];
  media_urls?: string[];
  scheduled_at?: string | null;
  soundEffects?: SoundEffectEntry[];
  emojiOverlays?: EmojiOverlayEntry[];
  customizeMode?: boolean;
  variantStates?: Record<string, VariantState>;
  savedAt: number;
}

function saveDraftToSession(data: DraftSnapshot) {
  try {
    sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(data));
  } catch {
    /* storage full — ignore */
  }
}

function loadDraftFromSession(): DraftSnapshot | null {
  try {
    const raw = sessionStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as DraftSnapshot;
    // 30분 이상 지난 스냅샷은 무시
    if (Date.now() - parsed.savedAt > 30 * 60 * 1000) {
      sessionStorage.removeItem(DRAFT_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function clearDraftFromSession() {
  sessionStorage.removeItem(DRAFT_STORAGE_KEY);
}

const { Title, Text } = Typography;

const PLATFORM_OPTIONS = [
  { value: 'YOUTUBE', label: 'YouTube' },
  { value: 'INSTAGRAM', label: 'Instagram' },
  { value: 'FACEBOOK', label: 'Facebook' },
  { value: 'X', label: 'X (Twitter)' },
  { value: 'NAVER_BLOG', label: '네이버 블로그' },
];

type ToolType = 'effects' | 'emoji' | 'ai';

const TOOL_OPTIONS = [
  { value: 'effects', label: '🎵 효과음' },
  { value: 'emoji', label: '😊 이모지' },
  { value: 'ai', label: '🤖 AI 어시스턴트' },
];

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

  // AI mutations (used for ai_generated flag in submit)
  const titleMutation = useGenerateTitle();
  const descriptionMutation = useGenerateDescription();
  const hashtagMutation = useGenerateHashtags();

  // UI state
  const [activeTool, setActiveTool] = useState<ToolType | null>(null);
  const [contentInfoOpen, setContentInfoOpen] = useState(false);
  const [platformSettingsOpen, setPlatformSettingsOpen] = useState(false);
  const [reviewConfirmOpen, setReviewConfirmOpen] = useState(false);
  const [customizeMode, setCustomizeMode] = useState(false);
  const [variantStates, setVariantStates] = useState<Record<string, VariantState>>({});
  const [soundEffects, setSoundEffects] = useState<SoundEffectEntry[]>([]);
  const [emojiOverlays, setEmojiOverlays] = useState<EmojiOverlayEntry[]>([]);
  const [mediaAssetId, setMediaAssetId] = useState<string | null>(null);
  const [subtitleModalOpen, setSubtitleModalOpen] = useState(false);
  const [shortformModalOpen, setShortformModalOpen] = useState(false);
  const mediaRef = useRef<MediaMainAreaHandle>(null);

  // Watched form fields
  const watchedTitle = Form.useWatch('title', form);
  const watchedPlatforms = Form.useWatch('platforms', form) as string[] | undefined;
  // 편집 모드에서 source_media_id를 mediaAssetId에 반영
  useEffect(() => {
    if (content?.source_media_id) {
      setMediaAssetId(content.source_media_id);
    }
  }, [content]);

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

    // Load effects/emoji from metadata
    if (content.metadata) {
      const meta = content.metadata as Record<string, unknown>;
      if (Array.isArray(meta.sound_effects)) {
        setSoundEffects(meta.sound_effects as SoundEffectEntry[]);
      }
      if (Array.isArray(meta.emoji_overlays)) {
        setEmojiOverlays(meta.emoji_overlays as EmojiOverlayEntry[]);
      }
    }

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

  // ── 세션 복원: 새 콘텐츠 작성 모드에서 페이지 복귀 시 이전 입력 복원 ──
  useEffect(() => {
    if (isEditMode) return; // 편집 모드는 서버 데이터 사용
    const snapshot = loadDraftFromSession();
    if (!snapshot) return;
    form.setFieldsValue({
      title: snapshot.title,
      body: snapshot.body,
      platforms: snapshot.platforms ?? [],
      channel_ids: snapshot.channel_ids ?? [],
      hashtags: snapshot.hashtags ?? [],
      media_urls: snapshot.media_urls ?? [],
      scheduled_at: snapshot.scheduled_at ? dayjs(snapshot.scheduled_at) : undefined,
    });
    if (snapshot.soundEffects) setSoundEffects(snapshot.soundEffects);
    if (snapshot.emojiOverlays) setEmojiOverlays(snapshot.emojiOverlays);
    if (snapshot.customizeMode) setCustomizeMode(snapshot.customizeMode);
    if (snapshot.variantStates) setVariantStates(snapshot.variantStates);
    if (snapshot.media_urls && snapshot.media_urls.length > 0) {
      message.info('이전 작업 내용이 복원되었습니다.');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── 세션 자동 저장: 폼 값 변경 시 sessionStorage에 스냅샷 저장 ──
  useEffect(() => {
    if (isEditMode) return; // 편집 모드는 서버에 저장됨
    const timer = setInterval(() => {
      const values = form.getFieldsValue(true);
      const mediaUrls = (values.media_urls as string[]) ?? [];
      // 입력이 하나라도 있을 때만 저장
      const hasAnyInput =
        values.title || values.body || mediaUrls.length > 0 ||
        (values.platforms as string[])?.length > 0;
      if (!hasAnyInput) return;
      saveDraftToSession({
        title: values.title as string,
        body: values.body as string,
        platforms: values.platforms as string[],
        channel_ids: values.channel_ids as string[],
        hashtags: values.hashtags as string[],
        media_urls: mediaUrls.filter((url: string) => !url.startsWith('blob:')),
        scheduled_at: values.scheduled_at
          ? (values.scheduled_at as { toISOString: () => string }).toISOString()
          : null,
        soundEffects,
        emojiOverlays,
        customizeMode,
        variantStates,
        savedAt: Date.now(),
      });
    }, 3000); // 3초마다 자동 저장
    return () => clearInterval(timer);
  }, [isEditMode, form, soundEffects, emojiOverlays, customizeMode, variantStates]);

  // Variant state handler
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

    // Include effects/emoji in metadata
    if (soundEffects.length > 0 || emojiOverlays.length > 0) {
      data.metadata = {
        ...(data.metadata ?? {}),
        ...(soundEffects.length > 0 ? { sound_effects: soundEffects } : {}),
        ...(emojiOverlays.length > 0 ? { emoji_overlays: emojiOverlays } : {}),
      };
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
    try {
      await form.validateFields(['title']);
    } catch {
      message.warning('제목을 입력하세요.');
      setContentInfoOpen(true);
      return;
    }
    try {
      if (isEditMode) {
        const data = buildUpdateData(form.getFieldsValue(true));
        await saveDraftMutation.mutateAsync({ id, data });
      } else {
        const data = buildCreateData(form.getFieldsValue(true));
        const result = await createMutation.mutateAsync(data);
        // 생성 후 에디터에 머물면서 편집 모드로 전환 (URL만 교체)
        navigate(`/contents/${result.id}/edit`, { replace: true });
      }
      clearDraftFromSession();
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
      clearDraftFromSession();
      message.success(CONTENT_MESSAGES.REQUEST_REVIEW_SUCCESS);
      setReviewConfirmOpen(false);
      if (isEditMode) navigate(`/contents/${id}`);
    } catch {
      message.error(CONTENT_MESSAGES.REQUEST_REVIEW_ERROR);
    }
  };

  const isSaving =
    createMutation.isPending || updateMutation.isPending || saveDraftMutation.isPending;

  if (isEditMode && isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl">
      <Form
        form={form}
        layout="vertical"
        initialValues={{ platforms: [], channel_ids: [], media_urls: [] }}
      >
        {/* ── 헤더 ── */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex shrink-0 items-center gap-3">
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/contents')}
            />
            <Title level={4} className="!mb-0 whitespace-nowrap">
              {isEditMode ? '콘텐츠 편집' : '새 콘텐츠 작성'}
            </Title>
            {isEditMode && content && <Tag color="blue">{content.status}</Tag>}
          </div>
          <Space wrap>
            <Button icon={<EditOutlined />} onClick={() => setContentInfoOpen(true)}>
              콘텐츠 정보
            </Button>
            <Button icon={<SettingOutlined />} onClick={() => setPlatformSettingsOpen(true)}>
              플랫폼 설정
            </Button>
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

        {/* 헤더 요약 정보 */}
        {watchedTitle && (
          <div className="mb-3 flex items-center gap-2">
            <Text type="secondary" className="text-sm">
              제목: {watchedTitle}
            </Text>
            {watchedPlatforms && watchedPlatforms.length > 0 && (
              <Space size={2}>
                {watchedPlatforms.map((p: string) => {
                  const opt = PLATFORM_OPTIONS.find((o) => o.value === p);
                  return (
                    <Tag key={p} className="text-xs">
                      {opt?.label || p}
                    </Tag>
                  );
                })}
              </Space>
            )}
          </div>
        )}

        {/* ── 메인: 미디어 영역 ── */}
        <div className="mb-4 rounded-lg border border-gray-200 bg-white p-4">
          <Form.Item name="media_urls" noStyle>
            <MediaMainArea ref={mediaRef} maxFiles={10} onAssetIdChange={setMediaAssetId} />
          </Form.Item>
        </div>

        {/* ── 도구 바 (영상 편집 모달 버튼 + Segmented) ── */}
        <div className="mb-4 flex items-center gap-3 overflow-x-auto">
          <Space size={4}>
            <Button
              onClick={() => setSubtitleModalOpen(true)}
              disabled={!mediaAssetId}
              title={mediaAssetId ? undefined : '영상을 먼저 업로드하세요'}
            >
              🎬 자막 편집
            </Button>
            <Button
              onClick={() => setShortformModalOpen(true)}
              disabled={!mediaAssetId}
              title={mediaAssetId ? undefined : '영상을 먼저 업로드하세요'}
            >
              ✂️ 숏폼 추출
            </Button>
          </Space>
          <Segmented
            value={activeTool ?? ''}
            onChange={(v) => setActiveTool(v ? (v as ToolType) : null)}
            options={[
              { value: '', label: '도구 선택' },
              ...TOOL_OPTIONS,
            ]}
          />
        </div>

        {/* ── 활성 패널 ── */}
        {activeTool === 'effects' && (
          <EffectsPanel
            contentText={
              [form.getFieldValue('title'), form.getFieldValue('body')]
                .filter(Boolean)
                .join('\n')
            }
            effects={soundEffects}
            onEffectsChange={setSoundEffects}
          />
        )}

        {activeTool === 'emoji' && (
          <EmojiPanel
            contentText={
              [form.getFieldValue('title'), form.getFieldValue('body')]
                .filter(Boolean)
                .join('\n')
            }
            emojis={emojiOverlays}
            onEmojisChange={setEmojiOverlays}
          />
        )}

        {activeTool === 'ai' && <AiAssistantPanel form={form} />}

        {/* ── 모달: 콘텐츠 정보 ── */}
        <ContentInfoModal
          open={contentInfoOpen}
          onClose={() => setContentInfoOpen(false)}
          form={form}
        />

        {/* ── 모달: 플랫폼 설정 ── */}
        <PlatformSettingsModal
          open={platformSettingsOpen}
          onClose={() => setPlatformSettingsOpen(false)}
          form={form}
          customizeMode={customizeMode}
          onCustomizeModeChange={setCustomizeMode}
          variantStates={variantStates}
          onVariantChange={handleVariantChange}
        />

        {/* ── 모달: 자막 편집기 ── */}
        <SubtitleEditorModal
          open={subtitleModalOpen}
          onClose={() => setSubtitleModalOpen(false)}
          assetId={mediaAssetId}
        />

        {/* ── 모달: 숏폼 편집기 ── */}
        <ShortformEditorModal
          open={shortformModalOpen}
          onClose={() => setShortformModalOpen(false)}
          assetId={mediaAssetId}
        />
      </Form>

      {/* ── 모달: 검수 요청 확인 ── */}
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
    </div>
  );
}
