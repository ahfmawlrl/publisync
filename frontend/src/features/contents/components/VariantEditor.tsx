import { RobotOutlined } from '@ant-design/icons';
import { Button, Card, Col, Form, Input, Row, Select, Typography } from 'antd';

import { useGenerateDescription, useGenerateHashtags, useGenerateTitle } from '@/features/ai/hooks/useAi';
import PlatformPreview from './PlatformPreview';

const { TextArea } = Input;

interface ChannelOption {
  value: string;
  label: string;
}

interface VariantEditorProps {
  platform: string;
  /** 현재 variant 데이터 (편집 모드). null이면 새 variant. */
  title: string;
  body: string;
  hashtags: string[];
  channelId: string | null;
  /** 해당 플랫폼의 ACTIVE 채널 목록 */
  channelOptions: ChannelOption[];
  /** 공통 정보 (variant에서 비어있을 때 미리보기에 사용) */
  commonTitle: string;
  commonBody: string;
  commonHashtags: string[];
  onChange: (field: 'title' | 'body' | 'hashtags' | 'channel_id', value: unknown) => void;
}

const PLATFORM_LABELS: Record<string, string> = {
  YOUTUBE: 'YouTube',
  INSTAGRAM: 'Instagram',
  FACEBOOK: 'Facebook',
  X: 'X (Twitter)',
  NAVER_BLOG: '네이버 블로그',
};

export default function VariantEditor({
  platform,
  title,
  body,
  hashtags,
  channelId,
  channelOptions,
  commonTitle,
  commonBody,
  commonHashtags,
  onChange,
}: VariantEditorProps) {
  const titleMutation = useGenerateTitle();
  const descMutation = useGenerateDescription();
  const hashtagMutation = useGenerateHashtags();

  // 미리보기: variant 값이 있으면 우선, 없으면 공통 정보
  const previewTitle = title || commonTitle || '제목을 입력하세요';
  const previewBody = body || commonBody || '';
  const previewHashtags = hashtags.length > 0 ? hashtags : commonHashtags;

  const getContentText = (): string | null => {
    const text = body || commonBody;
    if (!text || text.trim().length < 10) return null;
    return text.trim();
  };

  return (
    <Row gutter={16}>
      <Col xs={24} lg={14}>
        <Card title={`${PLATFORM_LABELS[platform] || platform} 커스터마이즈`} size="small">
          {channelOptions.length > 0 && (
            <div className="mb-3">
              <Typography.Text className="text-xs text-gray-500">게시 채널</Typography.Text>
              <Select
                placeholder="채널 선택"
                value={channelId ?? undefined}
                onChange={(v) => onChange('channel_id', v || null)}
                options={channelOptions}
                allowClear
                className="mt-1 w-full"
              />
            </div>
          )}

          <div className="mb-3">
            <Typography.Text className="text-xs text-gray-500">
              제목 오버라이드 (비우면 공통 제목 사용)
            </Typography.Text>
            <Input
              placeholder={commonTitle || '공통 제목 사용'}
              value={title}
              onChange={(e) => onChange('title', e.target.value)}
              maxLength={500}
              className="mt-1"
            />
            <Button
              type="link"
              size="small"
              icon={<RobotOutlined />}
              loading={titleMutation.isPending}
              className="mt-1 !p-0"
              onClick={() => {
                const text = getContentText();
                if (text) {
                  titleMutation.mutate(
                    { content_text: text, platform, count: 3 },
                    {
                      onSuccess: (data) => {
                        if (data?.suggestions?.[0]) {
                          onChange('title', data.suggestions[0]);
                        }
                      },
                    },
                  );
                }
              }}
            >
              AI 제목 제안
            </Button>
          </div>

          <div className="mb-3">
            <Typography.Text className="text-xs text-gray-500">
              본문 오버라이드 (비우면 공통 본문 사용)
            </Typography.Text>
            <TextArea
              placeholder={commonBody ? commonBody.slice(0, 50) + '...' : '공통 본문 사용'}
              value={body}
              onChange={(e) => onChange('body', e.target.value)}
              rows={6}
              className="mt-1"
            />
            <Button
              type="link"
              size="small"
              icon={<RobotOutlined />}
              loading={descMutation.isPending}
              className="mt-1 !p-0"
              onClick={() => {
                const text = getContentText();
                if (text) {
                  descMutation.mutate(
                    { content_text: text, platform, count: 2 },
                    {
                      onSuccess: (data) => {
                        if (data?.suggestions?.[0]) {
                          onChange('body', data.suggestions[0]);
                        }
                      },
                    },
                  );
                }
              }}
            >
              AI 본문 제안
            </Button>
          </div>

          <div className="mb-3">
            <Typography.Text className="text-xs text-gray-500">
              해시태그 오버라이드 (비우면 공통 해시태그 사용)
            </Typography.Text>
            <Select
              mode="tags"
              placeholder={commonHashtags.length > 0 ? commonHashtags.join(' ') : '공통 해시태그 사용'}
              value={hashtags}
              onChange={(v) => onChange('hashtags', v)}
              tokenSeparators={[' ', ',']}
              className="mt-1 w-full"
            />
            <Button
              type="link"
              size="small"
              icon={<RobotOutlined />}
              loading={hashtagMutation.isPending}
              className="mt-1 !p-0"
              onClick={() => {
                const text = getContentText();
                if (text) {
                  hashtagMutation.mutate(
                    { content_text: text, platform, count: 5 },
                    {
                      onSuccess: (data) => {
                        if (data?.hashtags) {
                          onChange('hashtags', data.hashtags);
                        }
                      },
                    },
                  );
                }
              }}
            >
              AI 해시태그 추천
            </Button>
          </div>
        </Card>
      </Col>

      <Col xs={24} lg={10}>
        <PlatformPreview
          platform={platform}
          title={previewTitle}
          body={previewBody}
          hashtags={previewHashtags}
        />
      </Col>
    </Row>
  );
}
