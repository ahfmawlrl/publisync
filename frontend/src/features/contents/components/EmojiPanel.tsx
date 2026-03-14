/**
 * EmojiPanel — 이모지 오버레이 AI 추천 + 수동 관리 인라인 패널.
 *
 * ContentEditorPage 도구 바에서 [이모지] 선택 시 표시.
 * AI 추천(useSuggestEffects)으로 이모지 제안을 받고,
 * 수동으로 이모지 항목을 추가/편집/삭제할 수 있음.
 * 데이터는 metadata JSONB의 emoji_overlays 필드에 저장.
 */

import { DeleteOutlined, PlusOutlined, SmileOutlined } from '@ant-design/icons';
import { App, Button, Card, Empty, Input, InputNumber, List, Space, Typography } from 'antd';
import { useCallback } from 'react';

import AiSuggestionPanel from '@/features/ai/components/AiSuggestionPanel';
import { useSuggestEffects } from '@/features/ai/hooks/useAi';

const { Text } = Typography;

export interface EmojiOverlayEntry {
  id: string;
  emoji: string;
  timestamp: number;
  duration: number;
  position: string;
}

const POSITION_OPTIONS = ['좌상', '우상', '중앙', '좌하', '우하'];

interface EmojiPanelProps {
  contentText: string;
  emojis: EmojiOverlayEntry[];
  onEmojisChange: (emojis: EmojiOverlayEntry[]) => void;
}

let nextEmojiId = 1;

export default function EmojiPanel({
  contentText,
  emojis,
  onEmojisChange,
}: EmojiPanelProps) {
  const { message } = App.useApp();
  const suggestMutation = useSuggestEffects();

  const handleAiSuggest = useCallback(() => {
    if (!contentText || contentText.trim().length < 5) {
      message.warning('콘텐츠 텍스트가 5자 이상이어야 AI 추천이 가능합니다.');
      return;
    }
    suggestMutation.mutate({
      content_text: contentText,
      content_type: 'emoji_overlays',
      count: 5,
    });
  }, [contentText, suggestMutation, message]);

  const handleAddEmoji = useCallback(() => {
    const newEmoji: EmojiOverlayEntry = {
      id: `emoji-${nextEmojiId++}`,
      emoji: '😊',
      timestamp: 0,
      duration: 3,
      position: '중앙',
    };
    onEmojisChange([...emojis, newEmoji]);
  }, [emojis, onEmojisChange]);

  const handleUpdateEmoji = useCallback(
    (id: string, field: keyof EmojiOverlayEntry, value: unknown) => {
      onEmojisChange(
        emojis.map((e) => (e.id === id ? { ...e, [field]: value } : e)),
      );
    },
    [emojis, onEmojisChange],
  );

  const handleRemoveEmoji = useCallback(
    (id: string) => {
      onEmojisChange(emojis.filter((e) => e.id !== id));
    },
    [emojis, onEmojisChange],
  );

  const handleApplySuggestion = useCallback(
    (content: string) => {
      const newEmoji: EmojiOverlayEntry = {
        id: `emoji-${nextEmojiId++}`,
        emoji: content,
        timestamp: 0,
        duration: 3,
        position: '중앙',
      };
      onEmojisChange([...emojis, newEmoji]);
      message.success('이모지가 추가되었습니다.');
    },
    [emojis, onEmojisChange, message],
  );

  return (
    <Card size="small">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Button
          type="primary"
          size="small"
          icon={<SmileOutlined />}
          onClick={handleAiSuggest}
          loading={suggestMutation.isPending}
        >
          AI 이모지 추천
        </Button>
        <Button size="small" icon={<PlusOutlined />} onClick={handleAddEmoji}>
          수동 추가
        </Button>
      </div>

      {/* AI Suggestions */}
      {(suggestMutation.data?.suggestions?.length ?? 0) > 0 && (
        <div className="mb-3">
          <AiSuggestionPanel
            title="AI 이모지 추천"
            suggestions={suggestMutation.data?.suggestions ?? []}
            loading={false}
            onSelect={handleApplySuggestion}
            error={suggestMutation.data?.error}
            model={suggestMutation.data?.model}
            processingTimeMs={suggestMutation.data?.processing_time_ms}
          />
        </div>
      )}

      {/* Emoji List */}
      {emojis.length === 0 ? (
        <Empty
          description="이모지가 없습니다. AI 추천 또는 수동으로 추가하세요."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          dataSource={emojis}
          renderItem={(entry) => (
            <List.Item key={entry.id} className="!px-0">
              <div className="flex w-full items-center gap-2">
                <Input
                  size="small"
                  value={entry.emoji}
                  onChange={(e) =>
                    handleUpdateEmoji(entry.id, 'emoji', e.target.value)
                  }
                  placeholder="😊"
                  className="w-20"
                />
                <Space size={4}>
                  <InputNumber
                    size="small"
                    value={entry.timestamp}
                    onChange={(v) =>
                      handleUpdateEmoji(entry.id, 'timestamp', v ?? 0)
                    }
                    min={0}
                    step={0.5}
                    className="w-20"
                    addonAfter="초"
                  />
                  <InputNumber
                    size="small"
                    value={entry.duration}
                    onChange={(v) =>
                      handleUpdateEmoji(entry.id, 'duration', v ?? 1)
                    }
                    min={0.5}
                    step={0.5}
                    className="w-20"
                    addonAfter="초"
                  />
                </Space>
                <select
                  value={entry.position}
                  onChange={(e) =>
                    handleUpdateEmoji(entry.id, 'position', e.target.value)
                  }
                  className="rounded border border-gray-300 px-2 py-1 text-xs"
                >
                  {POSITION_OPTIONS.map((pos) => (
                    <option key={pos} value={pos}>
                      {pos}
                    </option>
                  ))}
                </select>
                <Button
                  type="text"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => handleRemoveEmoji(entry.id)}
                />
              </div>
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
