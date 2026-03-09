import { useMemo, useState } from 'react';
import {
  Alert,
  Card,
  Col,
  Empty,
  Row,
  Segmented,
  Spin,
  Table,
  Tag,
  Tooltip as AntTooltip,
  Typography,
} from 'antd';
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { useSentimentTrend } from '../hooks/useSentimentTrend';
import type { KeywordCloudItem, SentimentAlert } from '../types';

const { Title, Text } = Typography;

const PERIOD_OPTIONS = [
  { label: '7일', value: '7d' },
  { label: '30일', value: '30d' },
  { label: '90일', value: '90d' },
];

const SENTIMENT_COLORS: Record<string, string> = {
  POSITIVE: 'green',
  NEUTRAL: 'blue',
  NEGATIVE: 'orange',
  DANGEROUS: 'red',
};

const RISK_COLORS: Record<string, string> = {
  HIGH: 'red',
  MEDIUM: 'orange',
  LOW: 'green',
};

const CHART_COLORS = {
  positive: '#52c41a',
  neutral: '#1677ff',
  negative: '#faad14',
  dangerous: '#ff4d4f',
};

const SENTIMENT_HEX: Record<string, string> = {
  POSITIVE: '#52c41a',
  NEUTRAL: '#1677ff',
  NEGATIVE: '#faad14',
  DANGEROUS: '#ff4d4f',
};

/** Custom WordCloud: sized by frequency, colored by sentiment. */
function KeywordCloud({ items }: { items: KeywordCloudItem[] }) {
  const sized = useMemo(() => {
    if (!items.length) return [];
    const maxCount = Math.max(...items.map((i) => i.count));
    const minCount = Math.min(...items.map((i) => i.count));
    const range = maxCount - minCount || 1;
    return items.map((item) => {
      const ratio = (item.count - minCount) / range;
      const fontSize = 14 + ratio * 24; // 14px ~ 38px
      return { ...item, fontSize };
    });
  }, [items]);

  if (!sized.length) return <Empty description="키워드 데이터가 없습니다" />;

  return (
    <div className="flex flex-wrap items-center justify-center gap-2 px-2 py-4" style={{ minHeight: 200 }}>
      {sized.map((item) => (
        <AntTooltip key={item.keyword} title={`${item.keyword}: ${item.count}회 (${item.sentiment})`}>
          <span
            style={{
              fontSize: item.fontSize,
              color: SENTIMENT_HEX[item.sentiment] ?? SENTIMENT_HEX.NEUTRAL,
              fontWeight: item.fontSize > 28 ? 700 : 500,
              cursor: 'default',
              lineHeight: 1.4,
              transition: 'transform 0.2s',
            }}
            className="inline-block hover:scale-110"
          >
            {item.keyword}
          </span>
        </AntTooltip>
      ))}
    </div>
  );
}

export default function SentimentTrendPage() {
  const [period, setPeriod] = useState('30d');
  const { data, isLoading } = useSentimentTrend(period);

  const alertColumns = [
    {
      title: '키워드',
      dataIndex: 'keyword',
      key: 'keyword',
      render: (val: string) => <Text strong>{val}</Text>,
    },
    {
      title: '유형',
      dataIndex: 'type',
      key: 'type',
      render: (val: string) => (
        <Tag color={val === 'NEGATIVE_SURGE' ? 'red' : 'green'}>
          {val === 'NEGATIVE_SURGE' ? '부정 급증' : '긍정 급증'}
        </Tag>
      ),
    },
    {
      title: '변화율',
      dataIndex: 'change_rate',
      key: 'change_rate',
      render: (val: number) => `${val > 0 ? '+' : ''}${val.toFixed(1)}%`,
    },
    {
      title: '위험도',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (val: string) => <Tag color={RISK_COLORS[val] ?? 'default'}>{val}</Tag>,
    },
    {
      title: '신뢰도',
      dataIndex: 'confidence',
      key: 'confidence',
    },
    {
      title: '기간',
      dataIndex: 'timeframe',
      key: 'timeframe',
    },
  ];

  const keywordColumns = [
    {
      title: '키워드',
      dataIndex: 'keyword',
      key: 'keyword',
      render: (val: string) => <Text strong>{val}</Text>,
    },
    {
      title: '출현 빈도',
      dataIndex: 'count',
      key: 'count',
      align: 'right' as const,
      sorter: (a: KeywordCloudItem, b: KeywordCloudItem) => a.count - b.count,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '감성',
      dataIndex: 'sentiment',
      key: 'sentiment',
      render: (val: string) => (
        <Tag color={SENTIMENT_COLORS[val] ?? 'default'}>{val}</Tag>
      ),
    },
    {
      title: '변화',
      dataIndex: 'change',
      key: 'change',
      align: 'right' as const,
      render: (val: number) => (
        <Text type={val > 0 ? 'danger' : val < 0 ? 'success' : undefined}>
          {val > 0 ? '+' : ''}{val.toFixed(1)}%
        </Text>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  const hasAlerts = (data?.alerts?.length ?? 0) > 0;
  const negativeAlerts = data?.alerts?.filter((a: SentimentAlert) => a.type === 'NEGATIVE_SURGE') ?? [];

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          여론 동향 분석
        </Title>
        <Segmented
          options={PERIOD_OPTIONS}
          value={period}
          onChange={(val) => setPeriod(val as string)}
        />
      </div>

      {/* Alerts */}
      {negativeAlerts.length > 0 && (
        <div className="mb-4">
          {negativeAlerts.map((alert: SentimentAlert, idx: number) => (
            <Alert
              key={idx}
              type="warning"
              showIcon
              className="mb-2"
              message={`"${alert.keyword}" 부정 급증 감지`}
              description={`변화율 ${alert.change_rate > 0 ? '+' : ''}${alert.change_rate.toFixed(1)}% | 위험도: ${alert.risk_level} | ${alert.timeframe}`}
            />
          ))}
        </div>
      )}

      <Row gutter={[16, 16]}>
        {/* Sentiment trend chart */}
        <Col xs={24} lg={14}>
          <Card title="감성 추이">
            {(data?.sentiment_trend?.length ?? 0) > 0 ? (
              <ResponsiveContainer width="100%" height={360}>
                <AreaChart data={data?.sentiment_trend ?? []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(val) => val.slice(5)}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="positive"
                    name="긍정"
                    stackId="1"
                    stroke={CHART_COLORS.positive}
                    fill={CHART_COLORS.positive}
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="neutral"
                    name="중립"
                    stackId="1"
                    stroke={CHART_COLORS.neutral}
                    fill={CHART_COLORS.neutral}
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="negative"
                    name="부정"
                    stackId="1"
                    stroke={CHART_COLORS.negative}
                    fill={CHART_COLORS.negative}
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="dangerous"
                    name="위험"
                    stackId="1"
                    stroke={CHART_COLORS.dangerous}
                    fill={CHART_COLORS.dangerous}
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="감성 데이터가 없습니다" />
            )}
          </Card>
        </Col>

        {/* Keyword WordCloud + table */}
        <Col xs={24} lg={10}>
          <Card title="키워드 클라우드">
            <KeywordCloud items={data?.keyword_cloud ?? []} />
          </Card>
          <Card title="키워드 빈도 상세" className="mt-4">
            {(data?.keyword_cloud?.length ?? 0) > 0 ? (
              <Table<KeywordCloudItem>
                rowKey="keyword"
                columns={keywordColumns}
                dataSource={data?.keyword_cloud ?? []}
                pagination={{ pageSize: 10, showSizeChanger: false }}
                size="small"
              />
            ) : (
              <Empty description="키워드 데이터가 없습니다" />
            )}
          </Card>
        </Col>
      </Row>

      {/* Alerts table */}
      {hasAlerts && (
        <Card title="감성 알림 상세" className="mt-4">
          <Table<SentimentAlert>
            rowKey={(record, idx) => `${record.keyword}-${idx}`}
            columns={alertColumns}
            dataSource={data?.alerts ?? []}
            pagination={false}
            size="small"
          />
        </Card>
      )}
    </div>
  );
}
