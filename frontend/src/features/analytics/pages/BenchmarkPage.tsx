import { useState } from 'react';
import {
  Card,
  Col,
  Empty,
  Progress,
  Row,
  Segmented,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import { Award, TrendingUp, BarChart3 } from 'lucide-react';

import PageHeader from '@/shared/components/PageHeader';
import { useBenchmark, useOrgComparison } from '../hooks/useBenchmark';
import type { BenchmarkPlatformItem, OrgComparisonItem } from '../types';

const { Text } = Typography;

const PLATFORM_COLORS: Record<string, string> = {
  YOUTUBE: '#FF0000',
  INSTAGRAM: '#E4405F',
  FACEBOOK: '#1877F2',
  X: '#000000',
  NAVER_BLOG: '#03C75A',
};

const METRIC_LABELS: Record<string, string> = {
  total_views: '총 조회수',
  engagement_rate: '참여율 (%)',
  post_frequency: '게시 빈도',
  followers: '팔로워',
  avg_views: '평균 조회수',
};

export default function BenchmarkPage() {
  const [period, setPeriod] = useState('30d');
  const { data: benchmark, isLoading } = useBenchmark(period);
  const { data: orgComparison, isLoading: isCompLoading } = useOrgComparison(period);

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  // Prepare radar chart data
  const radarData = benchmark?.platforms?.flatMap((platform) =>
    platform.metrics.map((m) => ({
      metric: METRIC_LABELS[m.metric] || m.metric,
      percentile: m.percentile,
      platform: platform.platform,
    })),
  ) || [];

  // Prepare bar chart data (org vs industry)
  const barChartData = benchmark?.platforms?.map((platform) => {
    const viewsMetric = platform.metrics.find((m) => m.metric === 'total_views');
    const engMetric = platform.metrics.find((m) => m.metric === 'engagement_rate');
    return {
      platform: platform.platform,
      '조회수 (내 기관)': viewsMetric?.org_value || 0,
      '조회수 (업종 평균)': viewsMetric?.industry_average || 0,
      '참여율 (내 기관)': engMetric?.org_value || 0,
      '참여율 (업종 평균)': engMetric?.industry_average || 0,
    };
  }) || [];

  // Platform benchmark table columns
  const platformColumns = [
    {
      title: '플랫폼',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform: string) => (
        <Tag
          color={PLATFORM_COLORS[platform] ? undefined : 'default'}
          style={
            PLATFORM_COLORS[platform]
              ? { backgroundColor: PLATFORM_COLORS[platform], color: '#fff' }
              : undefined
          }
        >
          {platform}
        </Tag>
      ),
    },
    {
      title: '순위',
      dataIndex: 'rank',
      key: 'rank',
      render: (rank: number, record: BenchmarkPlatformItem) => (
        <Text strong>
          {rank} / {record.total_orgs}
        </Text>
      ),
    },
    {
      title: '총 조회수',
      key: 'views',
      render: (_: unknown, record: BenchmarkPlatformItem) => {
        const m = record.metrics.find((x) => x.metric === 'total_views');
        if (!m) return '-';
        const diff = m.org_value - m.industry_average;
        return (
          <Space direction="vertical" size={0}>
            <Text strong>{m.org_value.toLocaleString()}</Text>
            <Text type={diff >= 0 ? 'success' : 'danger'} className="text-xs">
              평균 {m.industry_average.toLocaleString()} ({diff >= 0 ? '+' : ''}
              {diff.toLocaleString()})
            </Text>
          </Space>
        );
      },
    },
    {
      title: '참여율',
      key: 'engagement',
      render: (_: unknown, record: BenchmarkPlatformItem) => {
        const m = record.metrics.find((x) => x.metric === 'engagement_rate');
        if (!m) return '-';
        const diff = m.org_value - m.industry_average;
        return (
          <Space direction="vertical" size={0}>
            <Text strong>{m.org_value}%</Text>
            <Text type={diff >= 0 ? 'success' : 'danger'} className="text-xs">
              평균 {m.industry_average}% ({diff >= 0 ? '+' : ''}
              {diff.toFixed(2)}%)
            </Text>
          </Space>
        );
      },
    },
    {
      title: '백분위',
      key: 'percentile',
      render: (_: unknown, record: BenchmarkPlatformItem) => {
        const avgPercentile =
          record.metrics.length > 0
            ? record.metrics.reduce((sum, m) => sum + m.percentile, 0) / record.metrics.length
            : 0;
        return (
          <Tooltip title={`상위 ${(100 - avgPercentile).toFixed(1)}%`}>
            <Progress
              percent={avgPercentile}
              size="small"
              strokeColor={
                avgPercentile >= 70 ? '#52c41a' : avgPercentile >= 40 ? '#faad14' : '#ff4d4f'
              }
              format={(val) => `${val?.toFixed(0)}%`}
            />
          </Tooltip>
        );
      },
    },
  ];

  // Org comparison table columns
  const orgColumns = [
    {
      title: '기관명',
      dataIndex: 'org_name',
      key: 'org_name',
      render: (name: string) => <Text strong>{name || '-'}</Text>,
    },
    {
      title: '플랫폼',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform: string) => <Tag>{platform}</Tag>,
    },
    {
      title: '총 조회수',
      dataIndex: 'total_views',
      key: 'total_views',
      sorter: (a: OrgComparisonItem, b: OrgComparisonItem) => a.total_views - b.total_views,
      render: (val: number) => val.toLocaleString(),
    },
    {
      title: '총 좋아요',
      dataIndex: 'total_likes',
      key: 'total_likes',
      sorter: (a: OrgComparisonItem, b: OrgComparisonItem) => a.total_likes - b.total_likes,
      render: (val: number) => val.toLocaleString(),
    },
    {
      title: '참여율 (%)',
      dataIndex: 'engagement_rate',
      key: 'engagement_rate',
      sorter: (a: OrgComparisonItem, b: OrgComparisonItem) =>
        a.engagement_rate - b.engagement_rate,
      render: (val: number) => `${val}%`,
    },
    {
      title: '게시 수',
      dataIndex: 'post_count',
      key: 'post_count',
      sorter: (a: OrgComparisonItem, b: OrgComparisonItem) => a.post_count - b.post_count,
    },
  ];

  return (
    <div>
      <PageHeader
        title="벤치마크 분석"
        subtitle="업종 평균 대비 우리 기관의 소셜 미디어 성과를 비교합니다."
      />

      <div className="mb-4 flex items-center justify-between">
        <Segmented
          options={[
            { label: '7일', value: '7d' },
            { label: '30일', value: '30d' },
            { label: '90일', value: '90d' },
          ]}
          value={period}
          onChange={(val) => setPeriod(val as string)}
        />
        {benchmark?.updated_at && (
          <Text type="secondary" className="text-sm">
            마지막 업데이트: {new Date(benchmark.updated_at).toLocaleString('ko-KR')}
          </Text>
        )}
      </div>

      {/* Overall Score Card */}
      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="종합 점수"
              value={benchmark?.overall_score || 0}
              suffix="/ 100"
              prefix={<Award size={20} className="text-yellow-500" />}
              valueStyle={{
                color:
                  (benchmark?.overall_score || 0) >= 70
                    ? '#3f8600'
                    : (benchmark?.overall_score || 0) >= 40
                      ? '#cf8700'
                      : '#cf1322',
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="분석 플랫폼"
              value={benchmark?.platforms?.length || 0}
              suffix="개"
              prefix={<BarChart3 size={20} className="text-blue-500" />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="업종"
              value={benchmark?.industry || '공공기관'}
              prefix={<TrendingUp size={20} className="text-green-500" />}
            />
          </Card>
        </Col>
      </Row>

      {/* Platform Benchmark Table */}
      <Card title="플랫폼별 벤치마크" className="mb-4">
        {benchmark?.platforms && benchmark.platforms.length > 0 ? (
          <Table
            dataSource={benchmark.platforms}
            columns={platformColumns}
            rowKey="platform"
            pagination={false}
            size="middle"
          />
        ) : (
          <Empty description="벤치마크 데이터가 없습니다. 콘텐츠를 게시한 후 데이터가 축적됩니다." />
        )}
      </Card>

      {/* Charts Row */}
      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={24} lg={12}>
          <Card title="조회수 비교 (내 기관 vs 업종 평균)">
            {barChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={barChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="platform" />
                  <YAxis />
                  <RechartsTooltip />
                  <Legend />
                  <Bar dataKey="조회수 (내 기관)" fill="#1890ff" />
                  <Bar dataKey="조회수 (업종 평균)" fill="#bfbfbf" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="데이터 없음" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="성과 레이더 차트">
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" />
                  <PolarRadiusAxis domain={[0, 100]} />
                  <Radar
                    name="백분위"
                    dataKey="percentile"
                    stroke="#1890ff"
                    fill="#1890ff"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="데이터 없음" />
            )}
          </Card>
        </Col>
      </Row>

      {/* Organization Comparison */}
      <Card title="기관 비교" className="mb-4">
        {isCompLoading ? (
          <Spin />
        ) : orgComparison?.organizations && orgComparison.organizations.length > 0 ? (
          <Table
            dataSource={orgComparison.organizations}
            columns={orgColumns}
            rowKey={(record) => `${record.org_id}-${record.platform}`}
            pagination={{ pageSize: 10 }}
            size="middle"
          />
        ) : (
          <Empty description="비교할 기관 데이터가 없습니다." />
        )}
      </Card>
    </div>
  );
}
