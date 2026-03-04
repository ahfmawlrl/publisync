import { useMemo, useState } from 'react';
import { Button, Card, Col, Empty, Row, Select, Spin, Statistic, Table, Tag, Typography, message } from 'antd';
import {
  CommentOutlined,
  DownloadOutlined,
  EyeOutlined,
  LikeOutlined,
  ShareAltOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Heatmap } from '@ant-design/charts';

import type { PerformanceData } from '../types';
import { exportPerformance, useEngagementHeatmap, usePerformance } from '../hooks/useAnalytics';

const DAY_LABELS = ['월', '화', '수', '목', '금', '토', '일'] as const;
const HOUR_LABELS = Array.from({ length: 24 }, (_, i) => `${i}시`);

const { Title } = Typography;

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

const PERIOD_OPTIONS = [
  { label: '7일', value: '7d' },
  { label: '30일', value: '30d' },
  { label: '90일', value: '90d' },
];

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('30d');
  const [exporting, setExporting] = useState(false);
  const { data: performance, isLoading } = usePerformance({ period });
  const { data: heatmapData, isLoading: isHeatmapLoading } = useEngagementHeatmap(period);

  const heatmapChartData = useMemo(
    () =>
      (heatmapData ?? []).map((item) => ({
        hour: HOUR_LABELS[item.hour] ?? `${item.hour}시`,
        day: DAY_LABELS[item.day_of_week] ?? `${item.day_of_week}`,
        value: item.value,
      })),
    [heatmapData],
  );

  const heatmapConfig = useMemo(
    () => ({
      data: heatmapChartData,
      xField: 'hour',
      yField: 'day',
      colorField: 'value',
      legend: {
        color: {
          title: '참여율',
          position: 'bottom' as const,
        },
      },
      scale: {
        color: {
          range: ['#e8f4fd', '#b3d9f7', '#69b1ff', '#ffc069', '#ff7a45', '#f5222d'],
        },
      },
      mark: 'cell' as const,
      tooltip: {
        title: '참여율 상세',
        items: [
          { channel: 'x', name: '시간', valueFormatter: (v: string) => v },
          { channel: 'y', name: '요일', valueFormatter: (v: string) => v },
          { channel: 'color', name: '참여율', valueFormatter: (v: number) => `${v.toFixed(2)}%` },
        ],
      },
    }),
    [heatmapChartData],
  );

  // Aggregate totals across all platforms
  const totals = (performance ?? []).reduce(
    (acc, item) => ({
      views: acc.views + item.total_views,
      likes: acc.likes + item.total_likes,
      shares: acc.shares + item.total_shares,
      comments: acc.comments + item.total_comments,
    }),
    { views: 0, likes: 0, shares: 0, comments: 0 },
  );
  const totalInteractions = totals.likes + totals.shares + totals.comments;
  const overallEngagement = totals.views > 0 ? ((totalInteractions / totals.views) * 100).toFixed(2) : '0.00';

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportPerformance({ period });
      message.success('성과 데이터가 다운로드됩니다.');
    } catch {
      message.error('내보내기에 실패했습니다.');
    } finally {
      setExporting(false);
    }
  };

  const columns = [
    {
      title: '플랫폼',
      dataIndex: 'platform',
      key: 'platform',
      width: 160,
      render: (val: string) => (
        <Tag color={PLATFORM_COLORS[val] ?? 'default'}>{PLATFORM_LABELS[val] ?? val}</Tag>
      ),
    },
    {
      title: '조회수',
      dataIndex: 'total_views',
      key: 'total_views',
      align: 'right' as const,
      render: (val: number) => val.toLocaleString('ko-KR'),
    },
    {
      title: '좋아요',
      dataIndex: 'total_likes',
      key: 'total_likes',
      align: 'right' as const,
      render: (val: number) => val.toLocaleString('ko-KR'),
    },
    {
      title: '공유',
      dataIndex: 'total_shares',
      key: 'total_shares',
      align: 'right' as const,
      render: (val: number) => val.toLocaleString('ko-KR'),
    },
    {
      title: '댓글',
      dataIndex: 'total_comments',
      key: 'total_comments',
      align: 'right' as const,
      render: (val: number) => val.toLocaleString('ko-KR'),
    },
    {
      title: '참여율',
      dataIndex: 'engagement_rate',
      key: 'engagement_rate',
      align: 'right' as const,
      render: (val: number) => `${val}%`,
    },
  ];

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          성과 분석
        </Title>
        <div className="flex items-center gap-2">
          <Select
            value={period}
            options={PERIOD_OPTIONS}
            style={{ width: 120 }}
            onChange={setPeriod}
          />
          <Button icon={<DownloadOutlined />} loading={exporting} onClick={handleExport}>
            CSV 내보내기
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic title="총 조회수" value={totals.views} prefix={<EyeOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="총 좋아요"
              value={totals.likes}
              prefix={<LikeOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="총 공유"
              value={totals.shares}
              prefix={<ShareAltOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="총 댓글"
              value={totals.comments}
              prefix={<CommentOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="전체 참여율"
              value={overallEngagement}
              suffix="%"
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Platform comparison table */}
      <Card title="플랫폼별 성과 비교">
        <Table<PerformanceData>
          rowKey="platform"
          columns={columns}
          dataSource={performance ?? []}
          pagination={false}
          scroll={{ x: 700 }}
          locale={{ emptyText: '성과 데이터가 없습니다' }}
        />
      </Card>

      {/* Engagement heatmap */}
      <Card title="시간대별 참여율 히트맵" className="mt-4">
        {isHeatmapLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Spin size="large" />
          </div>
        ) : heatmapChartData.length === 0 ? (
          <Empty description="참여율 데이터가 없습니다" />
        ) : (
          <Heatmap {...heatmapConfig} />
        )}
      </Card>
    </div>
  );
}
