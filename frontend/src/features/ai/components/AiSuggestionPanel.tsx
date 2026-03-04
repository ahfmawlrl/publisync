/**
 * AiSuggestionPanel — Reusable AI suggestion display component (S11, F02).
 *
 * Shows a list of AI-generated suggestions with confidence scores.
 * Follows Human-in-the-Loop principle: user selects which suggestion to use.
 *
 * Usage:
 *   <AiSuggestionPanel
 *     title="AI 제목 제안"
 *     suggestions={data?.suggestions ?? []}
 *     loading={isPending}
 *     onSelect={(content) => form.setFieldValue('title', content)}
 *     error={data?.error}
 *   />
 */

import { RobotOutlined } from '@ant-design/icons';
import { Alert, Button, Empty, List, Progress, Space, Spin, Tag, Typography } from 'antd';

import type { AiSuggestion } from '../types';

const { Text } = Typography;

interface AiSuggestionPanelProps {
  /** Panel heading label. */
  title: string;
  /** AI-generated suggestions to display. */
  suggestions: AiSuggestion[];
  /** Callback when user selects a suggestion. */
  onSelect: (content: string) => void;
  /** Whether an AI request is in progress. */
  loading?: boolean;
  /** Error message from AI service. */
  error?: string | null;
  /** Model name used for generation. */
  model?: string;
  /** Processing time in milliseconds. */
  processingTimeMs?: number;
}

/** Score thresholds for visual feedback. */
function getScoreColor(score: number): string {
  if (score >= 0.85) return '#52c41a'; // green
  if (score >= 0.7) return '#1677ff';  // blue
  if (score >= 0.5) return '#faad14';  // gold
  return '#ff4d4f';                     // red
}

function getScoreLabel(score: number): string {
  if (score >= 0.85) return '높음';
  if (score >= 0.7) return '보통';
  if (score >= 0.5) return '낮음';
  return '매우 낮음';
}

export default function AiSuggestionPanel({
  title,
  suggestions,
  onSelect,
  loading = false,
  error,
  model,
  processingTimeMs,
}: AiSuggestionPanelProps) {
  // Loading state
  if (loading) {
    return (
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
        <Space>
          <Spin size="small" />
          <Text type="secondary">AI가 제안을 생성하고 있습니다...</Text>
        </Space>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert
        type="warning"
        showIcon
        icon={<RobotOutlined />}
        message="AI 제안 생성 실패"
        description={
          <Space direction="vertical" size={4}>
            <Text type="secondary">{error}</Text>
            <Text type="secondary">직접 입력하여 계속 작업할 수 있습니다.</Text>
          </Space>
        }
      />
    );
  }

  // No suggestions available
  if (suggestions.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="AI 제안을 받으려면 본문을 입력한 후 AI 제안 버튼을 클릭하세요."
        />
      </div>
    );
  }

  // Suggestions list
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <Space className="mb-3 w-full" direction="horizontal" align="center">
        <RobotOutlined className="text-blue-500" />
        <Text strong>{title}</Text>
        {model && (
          <Tag color="blue" className="ml-auto">
            {model}
          </Tag>
        )}
        {processingTimeMs !== undefined && (
          <Text type="secondary" className="text-xs">
            {(processingTimeMs / 1000).toFixed(1)}s
          </Text>
        )}
      </Space>

      <List
        size="small"
        dataSource={suggestions}
        renderItem={(item, index) => (
          <List.Item
            key={index}
            className="!border-blue-100"
            actions={[
              <Button
                key="use"
                type="link"
                size="small"
                onClick={() => onSelect(item.content)}
              >
                사용하기
              </Button>,
            ]}
          >
            <List.Item.Meta
              title={
                <Space size={8}>
                  <Text className="text-sm">{item.content}</Text>
                </Space>
              }
              description={
                <Space size={8} className="mt-1">
                  <Progress
                    percent={Math.round(item.score * 100)}
                    size="small"
                    strokeColor={getScoreColor(item.score)}
                    className="!mb-0 w-20"
                    format={() => ''}
                  />
                  <Tag
                    color={getScoreColor(item.score)}
                    className="text-xs"
                  >
                    {getScoreLabel(item.score)} ({Math.round(item.score * 100)}%)
                  </Tag>
                </Space>
              }
            />
          </List.Item>
        )}
      />

      <Text type="secondary" className="mt-2 block text-xs">
        AI가 생성한 제안입니다. 최종 결정은 사용자가 합니다.
      </Text>
    </div>
  );
}
