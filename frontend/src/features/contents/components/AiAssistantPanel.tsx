/**
 * AiAssistantPanel — AI 어시스턴트 인라인 패널.
 *
 * 톤 변환, 콘텐츠 검수, 번역, 썸네일 생성 기능을 하나의 패널에 통합.
 * 도구 바에서 [AI 어시스턴트] 선택 시 표시.
 */

import {
  CheckCircleOutlined,
  PictureOutlined,
  SwapOutlined,
  TranslationOutlined,
} from '@ant-design/icons';
import {
  Alert,
  App,
  Button,
  Card,
  Select,
  Segmented,
  Space,
  type FormInstance,
} from 'antd';
import { useState } from 'react';

import AiSuggestionPanel from '@/features/ai/components/AiSuggestionPanel';
import {
  useContentReview,
  useToneTransform,
  useTranslate,
} from '@/features/ai/hooks/useAi';
import { useCreateThumbnail, useJobStatus } from '@/features/ai/hooks/useAiJobs';

const PLATFORM_OPTIONS = [
  { value: 'YOUTUBE', label: 'YouTube' },
  { value: 'INSTAGRAM', label: 'Instagram' },
  { value: 'FACEBOOK', label: 'Facebook' },
  { value: 'X', label: 'X (Twitter)' },
  { value: 'NAVER_BLOG', label: '네이버 블로그' },
];

const TONE_OPTIONS = [
  { value: 'formal', label: '공식적' },
  { value: 'casual', label: '캐주얼' },
  { value: 'friendly', label: '친근한' },
  { value: 'professional', label: '전문적' },
];

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文' },
  { value: 'ja', label: '日本語' },
  { value: 'vi', label: 'Tiếng Việt' },
];

const THUMBNAIL_STYLE_OPTIONS = [
  { value: 'modern', label: '모던' },
  { value: 'minimalist', label: '미니멀' },
  { value: 'bold', label: '볼드' },
  { value: 'playful', label: '플레이풀' },
];

const THUMBNAIL_RATIO_OPTIONS = [
  { value: '16:9', label: '16:9 (YouTube)' },
  { value: '1:1', label: '1:1 (Instagram)' },
  { value: '9:16', label: '9:16 (Shorts/Reels)' },
];

type AiTool = 'tone' | 'review' | 'translate' | 'thumbnail';

interface AiAssistantPanelProps {
  form: FormInstance;
}

export default function AiAssistantPanel({ form }: AiAssistantPanelProps) {
  const { message } = App.useApp();
  const [activeTool, setActiveTool] = useState<AiTool>('tone');

  // Tone transform
  const [tonePlatform, setTonePlatform] = useState('YOUTUBE');
  const [toneTone, setToneTone] = useState('casual');
  const toneTransformMutation = useToneTransform();

  // Content review
  const contentReviewMutation = useContentReview();

  // Translate
  const [translateLang, setTranslateLang] = useState('en');
  const translateMutation = useTranslate();

  // Thumbnail
  const [thumbnailStyle, setThumbnailStyle] = useState('modern');
  const [thumbnailRatio, setThumbnailRatio] = useState('16:9');
  const thumbnailMutation = useCreateThumbnail();
  const [thumbnailJobId, setThumbnailJobId] = useState<string | null>(null);
  const thumbnailJobStatus = useJobStatus(thumbnailJobId);

  const getContentText = (): string | null => {
    const title = form.getFieldValue('title') as string | undefined;
    const body = form.getFieldValue('body') as string | undefined;
    const combined = [title, body].filter(Boolean).join('\n').trim();
    if (combined.length < 5) {
      message.warning('AI 기능을 사용하려면 제목 또는 본문을 5자 이상 입력하세요.');
      return null;
    }
    return combined;
  };

  return (
    <Card size="small">
      <Segmented
        block
        value={activeTool}
        onChange={(v) => setActiveTool(v as AiTool)}
        options={[
          { value: 'tone', label: '톤 변환', icon: <SwapOutlined /> },
          { value: 'review', label: '콘텐츠 검수', icon: <CheckCircleOutlined /> },
          { value: 'translate', label: '번역', icon: <TranslationOutlined /> },
          { value: 'thumbnail', label: '썸네일', icon: <PictureOutlined /> },
        ]}
        className="mb-4"
      />

      {/* 톤 변환 */}
      {activeTool === 'tone' && (
        <div className="space-y-3">
          <Space className="w-full" wrap>
            <Select
              value={tonePlatform}
              onChange={setTonePlatform}
              options={PLATFORM_OPTIONS}
              className="w-40"
              placeholder="플랫폼"
            />
            <Select
              value={toneTone}
              onChange={setToneTone}
              options={TONE_OPTIONS}
              className="w-32"
              placeholder="톤"
            />
            <Button
              type="primary"
              onClick={() => {
                const text = getContentText();
                if (text)
                  toneTransformMutation.mutate({
                    content_text: text,
                    target_platform: tonePlatform,
                    target_tone: toneTone,
                    count: 2,
                  });
              }}
              loading={toneTransformMutation.isPending}
            >
              변환
            </Button>
          </Space>
          {(toneTransformMutation.data?.suggestions?.length ?? 0) > 0 && (
            <AiSuggestionPanel
              title="톤 변환 결과"
              suggestions={toneTransformMutation.data?.suggestions ?? []}
              loading={false}
              onSelect={(c) => form.setFieldValue('body', c)}
              error={toneTransformMutation.data?.error}
              model={toneTransformMutation.data?.model}
              processingTimeMs={toneTransformMutation.data?.processing_time_ms}
            />
          )}
        </div>
      )}

      {/* 콘텐츠 검수 */}
      {activeTool === 'review' && (
        <div className="space-y-3">
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={() => {
              const text = getContentText();
              if (text)
                contentReviewMutation.mutate({
                  content_text: text,
                  check_spelling: true,
                  check_sensitivity: true,
                  check_bias: true,
                });
            }}
            loading={contentReviewMutation.isPending}
          >
            AI 콘텐츠 검수 실행
          </Button>
          {contentReviewMutation.data && !contentReviewMutation.isPending && (
            <Alert
              type={contentReviewMutation.data.issues?.length > 0 ? 'warning' : 'success'}
              message={contentReviewMutation.data.summary || '검수 완료'}
              description={
                contentReviewMutation.data.issues?.length > 0 ? (
                  <ul className="mt-2 space-y-1">
                    {contentReviewMutation.data.issues.map(
                      (issue: { severity: string; issue: string; suggestion: string }, idx: number) => (
                        <li key={idx} className="text-sm">
                          <strong>[{issue.severity}]</strong> {issue.issue}
                          {issue.suggestion && (
                            <span className="text-gray-500"> — {issue.suggestion}</span>
                          )}
                        </li>
                      ),
                    )}
                  </ul>
                ) : undefined
              }
              showIcon
            />
          )}
        </div>
      )}

      {/* 번역 */}
      {activeTool === 'translate' && (
        <div className="space-y-3">
          <Space>
            <Select
              value={translateLang}
              onChange={setTranslateLang}
              options={LANGUAGE_OPTIONS}
              className="w-40"
            />
            <Button
              type="primary"
              onClick={() => {
                const text = getContentText();
                if (text)
                  translateMutation.mutate({
                    content_text: text,
                    target_language: translateLang,
                  });
              }}
              loading={translateMutation.isPending}
            >
              번역
            </Button>
          </Space>
          {translateMutation.data && !translateMutation.isPending && (
            <AiSuggestionPanel
              title="번역 결과"
              suggestions={
                translateMutation.data.translated_text
                  ? [{ content: translateMutation.data.translated_text, score: translateMutation.data.confidence ?? 0.9 }]
                  : translateMutation.data.suggestions ?? []
              }
              loading={false}
              onSelect={(c) => form.setFieldValue('body', c)}
              error={translateMutation.data.error}
              model={translateMutation.data.model}
              processingTimeMs={translateMutation.data.processing_time_ms}
            />
          )}
        </div>
      )}

      {/* 썸네일 생성 */}
      {activeTool === 'thumbnail' && (
        <div className="space-y-3">
          <Space className="w-full" wrap>
            <Select
              value={thumbnailStyle}
              onChange={setThumbnailStyle}
              options={THUMBNAIL_STYLE_OPTIONS}
              className="w-32"
            />
            <Select
              value={thumbnailRatio}
              onChange={setThumbnailRatio}
              options={THUMBNAIL_RATIO_OPTIONS}
              className="w-40"
            />
            <Button
              type="primary"
              onClick={() => {
                const text = getContentText();
                if (text)
                  thumbnailMutation.mutate(
                    {
                      content_text: text,
                      style: thumbnailStyle,
                      count: 3,
                      aspect_ratio: thumbnailRatio,
                    },
                    {
                      onSuccess: (data) => setThumbnailJobId(data.job_id),
                      onError: () => message.error('AI 썸네일 생성 요청에 실패했습니다'),
                    },
                  );
              }}
              loading={thumbnailMutation.isPending}
            >
              생성
            </Button>
          </Space>
          {thumbnailJobStatus.data && (
            <Alert
              type={thumbnailJobStatus.data.status === 'COMPLETED' ? 'success' : 'info'}
              message={`상태: ${thumbnailJobStatus.data.status}`}
            />
          )}
        </div>
      )}
    </Card>
  );
}
