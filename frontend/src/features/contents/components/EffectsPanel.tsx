/**
 * EffectsPanel — 효과음 AI 추천 + 수동 관리 인라인 패널.
 *
 * ContentEditorPage 도구 바에서 [효과음] 선택 시 표시.
 * AI 추천(useSuggestEffects)으로 효과음 제안을 받고,
 * 수동으로 효과음 항목을 추가/편집/삭제할 수 있음.
 * 데이터는 metadata JSONB의 sound_effects 필드에 저장.
 */

import { DeleteOutlined, PlusOutlined, SoundOutlined } from '@ant-design/icons';
import { App, Button, Card, Empty, Input, InputNumber, List, Space, Typography } from 'antd';
import { useCallback } from 'react';

import AiSuggestionPanel from '@/features/ai/components/AiSuggestionPanel';
import { useSuggestEffects } from '@/features/ai/hooks/useAi';

const { Text } = Typography;

export interface SoundEffectEntry {
  id: string;
  name: string;
  timestamp: number;
  duration: number;
}

interface EffectsPanelProps {
  contentText: string;
  effects: SoundEffectEntry[];
  onEffectsChange: (effects: SoundEffectEntry[]) => void;
}

let nextEffectId = 1;

export default function EffectsPanel({
  contentText,
  effects,
  onEffectsChange,
}: EffectsPanelProps) {
  const { message } = App.useApp();
  const suggestEffectsMutation = useSuggestEffects();

  const handleAiSuggest = useCallback(() => {
    if (!contentText || contentText.trim().length < 5) {
      message.warning('콘텐츠 텍스트가 5자 이상이어야 AI 추천이 가능합니다.');
      return;
    }
    suggestEffectsMutation.mutate({
      content_text: contentText,
      content_type: 'sound_effects',
      count: 5,
    });
  }, [contentText, suggestEffectsMutation, message]);

  const handleAddEffect = useCallback(() => {
    const newEffect: SoundEffectEntry = {
      id: `effect-${nextEffectId++}`,
      name: '',
      timestamp: 0,
      duration: 2,
    };
    onEffectsChange([...effects, newEffect]);
  }, [effects, onEffectsChange]);

  const handleUpdateEffect = useCallback(
    (id: string, field: keyof SoundEffectEntry, value: unknown) => {
      onEffectsChange(
        effects.map((e) => (e.id === id ? { ...e, [field]: value } : e)),
      );
    },
    [effects, onEffectsChange],
  );

  const handleRemoveEffect = useCallback(
    (id: string) => {
      onEffectsChange(effects.filter((e) => e.id !== id));
    },
    [effects, onEffectsChange],
  );

  const handleApplySuggestion = useCallback(
    (content: string) => {
      const newEffect: SoundEffectEntry = {
        id: `effect-${nextEffectId++}`,
        name: content,
        timestamp: 0,
        duration: 2,
      };
      onEffectsChange([...effects, newEffect]);
      message.success('효과음이 추가되었습니다.');
    },
    [effects, onEffectsChange, message],
  );

  return (
    <Card size="small">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Button
          type="primary"
          size="small"
          icon={<SoundOutlined />}
          onClick={handleAiSuggest}
          loading={suggestEffectsMutation.isPending}
        >
          AI 효과음 추천
        </Button>
        <Button size="small" icon={<PlusOutlined />} onClick={handleAddEffect}>
          수동 추가
        </Button>
      </div>

      {/* AI Suggestions */}
      {(suggestEffectsMutation.data?.suggestions?.length ?? 0) > 0 && (
        <div className="mb-3">
          <AiSuggestionPanel
            title="AI 효과음 추천"
            suggestions={suggestEffectsMutation.data?.suggestions ?? []}
            loading={false}
            onSelect={handleApplySuggestion}
            error={suggestEffectsMutation.data?.error}
            model={suggestEffectsMutation.data?.model}
            processingTimeMs={suggestEffectsMutation.data?.processing_time_ms}
          />
        </div>
      )}

      {/* Effects List */}
      {effects.length === 0 ? (
        <Empty
          description="효과음이 없습니다. AI 추천 또는 수동으로 추가하세요."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          dataSource={effects}
          renderItem={(effect) => (
            <List.Item key={effect.id} className="!px-0">
              <div className="flex w-full items-center gap-2">
                <Input
                  size="small"
                  value={effect.name}
                  onChange={(e) =>
                    handleUpdateEffect(effect.id, 'name', e.target.value)
                  }
                  placeholder="효과음 이름"
                  className="flex-1"
                />
                <Space size={4}>
                  <InputNumber
                    size="small"
                    value={effect.timestamp}
                    onChange={(v) =>
                      handleUpdateEffect(effect.id, 'timestamp', v ?? 0)
                    }
                    min={0}
                    step={0.5}
                    className="w-20"
                    addonAfter="초"
                  />
                  <Text type="secondary" className="text-xs">
                    ~
                  </Text>
                  <InputNumber
                    size="small"
                    value={effect.duration}
                    onChange={(v) =>
                      handleUpdateEffect(effect.id, 'duration', v ?? 1)
                    }
                    min={0.5}
                    step={0.5}
                    className="w-20"
                    addonAfter="초"
                  />
                </Space>
                <Button
                  type="text"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => handleRemoveEffect(effect.id)}
                />
              </div>
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
