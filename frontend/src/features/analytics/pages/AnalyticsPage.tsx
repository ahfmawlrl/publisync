import { useMemo, useState } from 'react';
import { Button, Card, Col, Empty, List, Row, Select, Spin, Statistic, Tabs, Tag, Typography } from 'antd';
import {
  DownloadOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { Heatmap } from '@ant-design/charts';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { getPlatformConfig } from '@/shared/constants/platform';
import { exportPerformance, useEngagementHeatmap, usePerformance, useTopContents, useTrend } from '../hooks/useAnalytics';

const DAY_LABELS = ['월', '화', '수', '목', '금', '토', '일'] as const;
const HOUR_LABELS = Array.from({ length: 24 }, (_, i) => `${i}시`);

const { Title, Text } = Typography;

const PERIOD_OPTIONS = [
  { label: '7일', value: '7d' },
  { label: '30일', value: '30d' },
  { label: '90일', value: '90d' },
];

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('30d');
  const [exporting, setExporting] = useState(false);
  const [trendTab, setTrendTab] = useState('daily');
  const { data: performance, isLoading } = usePerformance({ period });
  const { data: heatmapData, isLoading: isHeatmapLoading } = useEngagementHeatmap(period);
  const { data: trendData, isLoading: isTrendLoading } = useTrend(period, trendTab);
  const { data: topContents } = useTopContents(period);

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

  // Compute optimal posting time from heatmap data
  const optimalTime = useMemo(() => {
    if (!heatmapData || heatmapData.length === 0) return null;
    const best = [...heatmapData].sort((a, b) => b.value - a.value)[0];
    const dayLabel = DAY_LABELS[best.day_of_week] ?? `${best.day_of_week}`;
    return `${dayLabel} ${best.hour}:00~${best.hour + 1}:00`;
  }, [heatmapData]);

  // Aggregate totals across all platforms
  const totals = (performance ?? []).reduce(
    (acc, item) => ({
      views: acc.views + item.total_views,
      followers: acc.followers + item.followers,
      contents: acc.contents + 1,
      engagement: acc.engagement + item.engagement_rate,
    }),
    { views: 0, followers: 0, contents: 0, engagement: 0 },
  );
  const avgEngagement = totals.contents > 0 ? (totals.engagement / totals.contents).toFixed(1) : '0.0';

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportPerformance({ period });
    } catch {
      // silently fail
    } finally {
      setExporting(false);
    }
  };

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

      {/* KPI Cards — 4 cards from API data */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="총 도달" value={totals.views} valueStyle={{ fontSize: 28 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="참여율" value={avgEngagement} suffix="%" valueStyle={{ fontSize: 28 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="팔로워" value={totals.followers} valueStyle={{ fontSize: 28 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="게시물" value={totals.contents} suffix="개 플랫폼" valueStyle={{ fontSize: 28 }} />
          </Card>
        </Col>
      </Row>

      {/* Reach & Engagement Trend line chart */}
      <Card className="mb-4" title="도달·참여 추이" size="small"
        extra={
          <Tabs
            size="small"
            activeKey={trendTab}
            onChange={setTrendTab}
            items={[
              { key: 'daily', label: '일별' },
              { key: 'weekly', label: '주별' },
              { key: 'monthly', label: '월별' },
            ]}
          />
        }
      >
        {isTrendLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Spin size="large" />
          </div>
        ) : trendData && trendData.length > 0 ? (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="reach" name="도달" stroke="#1677ff" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="engagement" name="참여" stroke="#52c41a" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-64 items-center justify-center">
            <Text type="secondary">추이 데이터가 없습니다</Text>
          </div>
        )}
      </Card>

      {/* Two-col: Platform comparison + Top 5 */}
      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={24} lg={12}>
          <Card title="플랫폼별 성과 비교" size="small">
            {performance && performance.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={performance} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis
                    type="category"
                    dataKey="platform"
                    width={100}
                    tickFormatter={(val: string) => getPlatformConfig(val).label}
                  />
                  <Tooltip />
                  <Bar dataKey="total_views" name="조회수" fill="#1677ff" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-60 items-center justify-center">
                <Text type="secondary">성과 데이터가 없습니다</Text>
              </div>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="상위 콘텐츠 TOP 5" size="small">
            <List
              dataSource={topContents ?? []}
              locale={{ emptyText: '콘텐츠가 없습니다' }}
              renderItem={(item) => (
                <List.Item>
                  <Text className="mr-2 font-mono text-sm">{item.rank}.</Text>
                  <div className="min-w-0 flex-1">
                    <Text className="text-sm">{item.title}</Text>
                    <Tag color={getPlatformConfig(item.platform).color} className="ml-2 !text-xs">
                      {getPlatformConfig(item.platform).short}
                    </Tag>
                  </div>
                  <Text type="secondary" className="text-sm">{item.metric_label}</Text>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* Engagement heatmap */}
      <Card title="게시 시간대별 참여율 히트맵" size="small">
        {isHeatmapLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Spin size="large" />
          </div>
        ) : heatmapChartData.length === 0 ? (
          <Empty description="참여율 데이터가 없습니다" />
        ) : (
          <Heatmap {...heatmapConfig} />
        )}
        {optimalTime && (
          <div className="mt-3 flex items-center gap-1 text-xs text-gray-500">
            <RobotOutlined />
            <span>최적 게시 시간 추천: {optimalTime}</span>
          </div>
        )}
      </Card>
    </div>
  );
}
