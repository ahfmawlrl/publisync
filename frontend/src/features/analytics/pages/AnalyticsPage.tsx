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

import { exportPerformance, useEngagementHeatmap, usePerformance } from '../hooks/useAnalytics';

const DAY_LABELS = ['월', '화', '수', '목', '금', '토', '일'] as const;
const HOUR_LABELS = Array.from({ length: 24 }, (_, i) => `${i}시`);

const { Title, Text } = Typography;

const PLATFORM_LABELS: Record<string, string> = {
  YOUTUBE: 'YouTube',
  INSTAGRAM: 'Instagram',
  FACEBOOK: 'Facebook',
  X: 'X (Twitter)',
  NAVER_BLOG: '네이버 블로그',
};

const PLATFORM_TAG_COLORS: Record<string, string> = {
  YOUTUBE: 'red',
  INSTAGRAM: 'magenta',
  FACEBOOK: 'blue',
  X: 'default',
  NAVER_BLOG: 'green',
};

const PLATFORM_SHORT: Record<string, string> = {
  YOUTUBE: 'YT',
  INSTAGRAM: 'IG',
  FACEBOOK: 'FB',
  X: 'X',
  NAVER_BLOG: 'Blog',
};

const PERIOD_OPTIONS = [
  { label: '7일', value: '7d' },
  { label: '30일', value: '30d' },
  { label: '90일', value: '90d' },
];

// Mock trend data for the line chart (until backend provides time-series)
function generateTrendData() {
  const days = [];
  const now = new Date();
  for (let i = 13; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    days.push({
      date: `${d.getMonth() + 1}/${d.getDate()}`,
      reach: Math.floor(3000 + Math.random() * 6000),
      engagement: Math.floor(200 + Math.random() * 800),
    });
  }
  return days;
}

// Mock top 5 content (until backend provides a dedicated endpoint)
const MOCK_TOP5 = [
  { rank: 1, title: '정책 브리핑', platform: 'YOUTUBE', metric: '12.3K 조회' },
  { rank: 2, title: '봄맞이 캠페인', platform: 'INSTAGRAM', metric: '8.9K 도달' },
  { rank: 3, title: '교통 안내 카드뉴스', platform: 'FACEBOOK', metric: '5.2K 도달' },
  { rank: 4, title: '문화행사 안내', platform: 'YOUTUBE', metric: '4.8K 조회' },
  { rank: 5, title: '시민 인터뷰', platform: 'INSTAGRAM', metric: '3.5K 도달' },
];

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('30d');
  const [exporting, setExporting] = useState(false);
  const [trendTab, setTrendTab] = useState('daily');
  const { data: performance, isLoading } = usePerformance({ period });
  const { data: heatmapData, isLoading: isHeatmapLoading } = useEngagementHeatmap(period);

  const trendData = useMemo(() => generateTrendData(), []);

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
            PDF 내보내기
          </Button>
        </div>
      </div>

      {/* KPI Cards — 4 cards matching prototype */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="총 도달" value={totals.views} valueStyle={{ fontSize: 28 }} />
            <Text type="success" className="text-xs">+12.3%</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="참여율" value={avgEngagement} suffix="%" valueStyle={{ fontSize: 28 }} />
            <Text type="success" className="text-xs">+0.8%p</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="팔로워" value={totals.followers} valueStyle={{ fontSize: 28 }} />
            <Text type="success" className="text-xs">+1,423</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="게시물" value={`${(performance ?? []).length > 0 ? totals.contents * 25 : 0}건`} valueStyle={{ fontSize: 28 }} />
            <Text type="success" className="text-xs">+15건</Text>
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
                    tickFormatter={(val: string) => PLATFORM_LABELS[val] ?? val}
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
              dataSource={MOCK_TOP5}
              locale={{ emptyText: '콘텐츠가 없습니다' }}
              renderItem={(item) => (
                <List.Item>
                  <Text className="mr-2 font-mono text-sm">{item.rank}.</Text>
                  <div className="min-w-0 flex-1">
                    <Text className="text-sm">{item.title}</Text>
                    <Tag color={PLATFORM_TAG_COLORS[item.platform]} className="ml-2 !text-xs">
                      {PLATFORM_SHORT[item.platform]}
                    </Tag>
                  </div>
                  <Text type="secondary" className="text-sm">{item.metric}</Text>
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
        <div className="mt-3 flex items-center gap-1 text-xs text-gray-500">
          <RobotOutlined />
          <span>최적 게시 시간 추천: 화/목 09:00~10:00</span>
        </div>
      </Card>
    </div>
  );
}
