import { useState } from 'react';
import {
  Button,
  Card,
  Col,
  Empty,
  Input,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { Target, Clock, FlaskConical } from 'lucide-react';

import { useOptimalTime, usePrediction } from '../hooks/usePrediction';
import type { AbTestSuggestion, OptimalTimeSlot, PredictionPlatformItem } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const PLATFORM_LABELS: Record<string, string> = {
  YOUTUBE: 'YouTube',
  INSTAGRAM: 'Instagram',
  FACEBOOK: 'Facebook',
  X: 'X (Twitter)',
  NAVER_BLOG: '네이버 블로그',
};

const PLATFORM_COLORS: Record<string, string> = {
  YOUTUBE: 'red',
  INSTAGRAM: 'magenta',
  FACEBOOK: 'blue',
  X: 'default',
  NAVER_BLOG: 'green',
};

export default function PredictionPage() {
  const [contentId, _setContentId] = useState<string | undefined>();
  const { data, isLoading } = usePrediction(contentId);
  const optimalTimeMutation = useOptimalTime();

  const [otForm, setOtForm] = useState({ content_text: '', platforms: ['YOUTUBE', 'INSTAGRAM'] });

  const handleOptimalTime = async () => {
    if (!otForm.content_text.trim()) return;
    try {
      await optimalTimeMutation.mutateAsync(otForm);
    } catch {
      // error handled by mutation
    }
  };

  const confidenceColor = (val: number) => {
    if (val >= 0.7) return '#52c41a';
    if (val >= 0.4) return '#faad14';
    return '#ff4d4f';
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  // Low data warning
  if (data && data.data_months < 3) {
    return (
      <div>
        <div className="mb-4 flex items-center gap-2">
          <Title level={4} className="!mb-0">
            콘텐츠 성과 예측
          </Title>
          <Tag color="blue">BETA</Tag>
        </div>
        <Card>
          <Empty
            description={
              <div className="text-center">
                <Paragraph>데이터가 부족합니다.</Paragraph>
                <Paragraph type="secondary">
                  정확한 예측을 위해 최소 3개월 이상의 성과 데이터가 필요합니다.
                  현재 {data.data_months}개월의 데이터가 축적되어 있습니다.
                </Paragraph>
              </div>
            }
          />
        </Card>
      </div>
    );
  }

  const platformColumns = [
    {
      title: '플랫폼',
      dataIndex: 'platform',
      key: 'platform',
      render: (val: string) => (
        <Tag color={PLATFORM_COLORS[val] ?? 'default'}>{PLATFORM_LABELS[val] ?? val}</Tag>
      ),
    },
    {
      title: '예상 조회수',
      key: 'estimated_views',
      render: (_: unknown, record: PredictionPlatformItem) =>
        record.estimated_views
          ? `${record.estimated_views.min.toLocaleString()} ~ ${record.estimated_views.max.toLocaleString()}`
          : '-',
    },
    {
      title: '예상 좋아요',
      key: 'estimated_likes',
      render: (_: unknown, record: PredictionPlatformItem) =>
        record.estimated_likes
          ? `${record.estimated_likes.min.toLocaleString()} ~ ${record.estimated_likes.max.toLocaleString()}`
          : '-',
    },
  ];

  const optimalTimeColumns = [
    {
      title: '요일',
      dataIndex: 'day_of_week',
      key: 'day_of_week',
      width: 80,
      render: (val: string) => <Text strong>{val}</Text>,
    },
    {
      title: '시간대',
      dataIndex: 'time_range',
      key: 'time_range',
      width: 140,
    },
    {
      title: '근거',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
    },
  ];

  const abTestColumns = [
    {
      title: '항목',
      dataIndex: 'field',
      key: 'field',
      width: 100,
      render: (val: string) => <Tag>{val}</Tag>,
    },
    {
      title: 'Option A',
      dataIndex: 'option_a',
      key: 'option_a',
      ellipsis: true,
    },
    {
      title: 'Option B',
      dataIndex: 'option_b',
      key: 'option_b',
      ellipsis: true,
    },
    {
      title: '예측',
      dataIndex: 'prediction',
      key: 'prediction',
      ellipsis: true,
    },
    {
      title: '근거',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
    },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex items-center gap-2">
        <Title level={4} className="!mb-0">
          콘텐츠 성과 예측
        </Title>
        <Tag color="blue">BETA</Tag>
      </div>

      {/* Confidence bar */}
      {data && (
        <Card className="mb-4">
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Text type="secondary">예측 신뢰도</Text>
              <Progress
                percent={Math.round((data.confidence ?? 0) * 100)}
                strokeColor={confidenceColor(data.confidence)}
                size="small"
              />
            </Col>
            <Col>
              <Statistic
                title="학습 데이터"
                value={data.data_months}
                suffix="개월"
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
          </Row>
        </Card>
      )}

      <Row gutter={[16, 16]}>
        {/* Platform predictions */}
        <Col xs={24} lg={14}>
          <Card
            title={
              <Space>
                <Target size={16} />
                <span>플랫폼별 예상 성과</span>
              </Space>
            }
          >
            {(data?.platform_predictions?.length ?? 0) > 0 ? (
              <Table<PredictionPlatformItem>
                rowKey="platform"
                columns={platformColumns}
                dataSource={data?.platform_predictions ?? []}
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="예측 데이터가 없습니다" />
            )}
          </Card>
        </Col>

        {/* Optimal publish times */}
        <Col xs={24} lg={10}>
          <Card
            title={
              <Space>
                <Clock size={16} />
                <span>최적 게시 시간</span>
              </Space>
            }
          >
            {(data?.optimal_publish_times?.length ?? 0) > 0 ? (
              <Table<OptimalTimeSlot>
                rowKey={(_, idx) => String(idx)}
                columns={optimalTimeColumns}
                dataSource={data?.optimal_publish_times ?? []}
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="최적 시간 데이터가 없습니다" />
            )}
          </Card>
        </Col>
      </Row>

      {/* A/B test suggestions */}
      {(data?.ab_test_suggestions?.length ?? 0) > 0 && (
        <Card
          title={
            <Space>
              <FlaskConical size={16} />
              <span>A/B 테스트 제안</span>
            </Space>
          }
          className="mt-4"
        >
          <Table<AbTestSuggestion>
            rowKey={(_, idx) => String(idx)}
            columns={abTestColumns}
            dataSource={data?.ab_test_suggestions ?? []}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      {/* AI Optimal Time Tool */}
      <Card
        title={
          <Space>
            <Clock size={16} />
            <span>AI 최적 게시 시간 추천</span>
          </Space>
        }
        className="mt-4"
      >
        <div className="space-y-3">
          <TextArea
            placeholder="콘텐츠 내용을 입력하세요..."
            rows={3}
            value={otForm.content_text}
            onChange={(e) => setOtForm((p) => ({ ...p, content_text: e.target.value }))}
          />
          <div className="flex items-center gap-2">
            <Select
              mode="multiple"
              value={otForm.platforms}
              onChange={(val) => setOtForm((p) => ({ ...p, platforms: val }))}
              options={Object.entries(PLATFORM_LABELS).map(([value, label]) => ({ value, label }))}
              style={{ minWidth: 300 }}
              placeholder="플랫폼 선택"
            />
            <Button
              type="primary"
              onClick={handleOptimalTime}
              loading={optimalTimeMutation.isPending}
              disabled={!otForm.content_text.trim()}
            >
              추천받기
            </Button>
          </div>

          {optimalTimeMutation.data && (
            <Card size="small" className="mt-2 bg-blue-50">
              <Text strong>AI 추천 결과</Text>
              <Table
                rowKey={(_, idx) => String(idx)}
                columns={optimalTimeColumns}
                dataSource={optimalTimeMutation.data.optimal_times ?? []}
                pagination={false}
                size="small"
                className="mt-2"
              />
              <Text type="secondary" className="mt-2 block">
                신뢰도: {Math.round((optimalTimeMutation.data.confidence ?? 0) * 100)}% | 모델: {optimalTimeMutation.data.model}
              </Text>
            </Card>
          )}
        </div>
      </Card>
    </div>
  );
}
