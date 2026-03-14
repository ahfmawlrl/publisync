/**
 * PlatformSettingsModal — 플랫폼 설정 모달.
 *
 * 플랫폼 선택, 채널 배정, 게시 모드(일괄/커스터마이즈), 변형본 편집.
 * 헤더의 [플랫폼 설정] 버튼 → 이 모달 오픈.
 */

import {
  Alert,
  Button,
  Checkbox,
  Form,
  Modal,
  Select,
  Switch,
  Tabs,
  Typography,
  type FormInstance,
} from 'antd';
import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { PaginatedResponse } from '@/shared/api/types';
import VariantEditor from './VariantEditor';

const { Text } = Typography;

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

interface ChannelOption {
  id: string;
  name: string;
  platform: string;
  status: string;
}

interface PlatformSettingsModalProps {
  open: boolean;
  onClose: () => void;
  form: FormInstance;
  customizeMode: boolean;
  onCustomizeModeChange: (v: boolean) => void;
  variantStates: Record<string, VariantState>;
  onVariantChange: (
    platform: string,
    field: 'title' | 'body' | 'hashtags' | 'channel_id',
    value: unknown,
  ) => void;
}

export default function PlatformSettingsModal({
  open,
  onClose,
  form,
  customizeMode,
  onCustomizeModeChange,
  variantStates,
  onVariantChange,
}: PlatformSettingsModalProps) {
  const watchedPlatforms = Form.useWatch('platforms', form) as string[] | undefined;
  const watchedTitle = Form.useWatch('title', form) as string | undefined;
  const watchedBody = Form.useWatch('body', form) as string | undefined;
  const watchedHashtags = Form.useWatch('hashtags', form) as string[] | undefined;

  // Fetch channels
  const { data: channelsData } = useQuery({
    queryKey: ['channels', 'all'],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<ChannelOption>>('/channels', {
        params: { limit: 100 },
      });
      return res.data.data;
    },
  });

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

  const uniformChannelOptions = useMemo(() => {
    if (!watchedPlatforms?.length) return [];
    return activeChannels
      .filter((ch) => watchedPlatforms.includes(ch.platform))
      .map((ch) => ({ value: ch.id, label: `${ch.name} (${ch.platform})` }));
  }, [activeChannels, watchedPlatforms]);

  const handleVariantChange = useCallback(
    (platform: string, field: 'title' | 'body' | 'hashtags' | 'channel_id', value: unknown) => {
      onVariantChange(platform, field, value);
    },
    [onVariantChange],
  );

  return (
    <Modal
      title="플랫폼 설정"
      open={open}
      onCancel={onClose}
      footer={
        <Button type="primary" onClick={onClose}>
          적용
        </Button>
      }
      width="80vw"
      styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
      destroyOnHidden={false}
    >
      <Form form={form} layout="vertical">
      <div className="space-y-4">
        {/* 플랫폼 선택 */}
        <Form.Item name="platforms" label="게시 플랫폼" className="!mb-2">
          <Checkbox.Group options={PLATFORM_OPTIONS} />
        </Form.Item>

        {/* 게시 모드 */}
        <div className="flex items-center gap-3">
          <Text>게시 모드:</Text>
          <Switch
            checked={customizeMode}
            onChange={onCustomizeModeChange}
            checkedChildren="플랫폼별 맞춤"
            unCheckedChildren="전체 동일"
          />
        </div>

        {/* 전체 동일 모드: 채널 선택 */}
        {!customizeMode && (
          <Form.Item name="channel_ids" label="게시 채널" className="!mb-2">
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

        {/* 플랫폼별 맞춤 모드: VariantEditor 탭 */}
        {customizeMode && watchedPlatforms && watchedPlatforms.length > 0 && (
          <Tabs
            items={watchedPlatforms.map((p: string) => {
              const opt = PLATFORM_OPTIONS.find((o) => o.value === p);
              const vs = variantStates[p] || {
                title: '',
                body: '',
                hashtags: [],
                channel_id: null,
              };
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
        )}

        {customizeMode && (!watchedPlatforms || watchedPlatforms.length === 0) && (
          <Alert
            type="info"
            message="플랫폼을 선택하면 플랫폼별 커스터마이즈 탭이 표시됩니다."
          />
        )}
      </div>
      </Form>
    </Modal>
  );
}
