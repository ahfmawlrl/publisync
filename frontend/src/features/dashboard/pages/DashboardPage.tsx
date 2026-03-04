import { CalendarOutlined, CheckCircleOutlined, EyeOutlined, FileTextOutlined, LinkOutlined } from '@ant-design/icons';
import { Card, Col, List, Row, Spin, Statistic, Tag, Typography } from 'antd';
import type { PieLabelRenderProps } from 'recharts';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import {
  useApprovalStatus,
  useDashboardSummary,
  usePlatformTrends,
  useRecentContents,
  useSentimentSummary,
  useTodaySchedule,
} from '../hooks/useDashboard';

const { Title, Text } = Typography;

const STATUS_LABELS: Record<string, string> = {
  PENDING_REVIEW: '검토 대기',
  IN_REVIEW: '검토 중',
  APPROVED: '승인됨',
  REJECTED: '반려됨',
};

const CONTENT_STATUS: Record<string, { color: string; text: string }> = {
  DRAFT: { color: 'default', text: '초안' },
  PENDING_REVIEW: { color: 'orange', text: '검토 대기' },
  IN_REVIEW: { color: 'processing', text: '검토 중' },
  APPROVED: { color: 'cyan', text: '승인됨' },
  SCHEDULED: { color: 'blue', text: '예약됨' },
  PUBLISHING: { color: 'processing', text: '게시 중' },
  PUBLISHED: { color: 'green', text: '게시 완료' },
  PARTIALLY_PUBLISHED: { color: 'warning', text: '부분 게시' },
  PUBLISH_FAILED: { color: 'error', text: '게시 실패' },
};

const SENTIMENT_COLORS: Record<string, string> = {
  POSITIVE: '#52c41a',
  NEUTRAL: '#1677ff',
  NEGATIVE: '#faad14',
  DANGEROUS: '#ff4d4f',
};

const SENTIMENT_LABELS: Record<string, string> = {
  POSITIVE: '긍정',
  NEUTRAL: '중립',
  NEGATIVE: '부정',
  DANGEROUS: '위험',
};

export default function DashboardPage() {
  const { data: summary, isLoading } = useDashboardSummary();
  const { data: recentContents } = useRecentContents();
  const { data: todaySchedule } = useTodaySchedule();
  const { data: approvalStatus } = useApprovalStatus();
  const { data: sentimentData } = useSentimentSummary();
  const { data: platformTrends } = usePlatformTrends();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={4} className="!mb-4">대시보드</Title>

      {/* KPI Cards */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="전체 콘텐츠"
              value={summary?.total_contents ?? 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="게시 완료"
              value={summary?.published_contents ?? 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="예약됨"
              value={summary?.scheduled_contents ?? 0}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="승인 대기"
              value={summary?.pending_approvals ?? 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="활성 채널"
              value={summary?.active_channels ?? 0}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card>
            <Statistic
              title="총 조회수"
              value={summary?.total_views ?? 0}
              prefix={<EyeOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]} className="mb-6">
        {/* Sentiment Donut Chart */}
        <Col xs={24} lg={8}>
          <Card title="댓글 감성 분석" size="small">
            {sentimentData && sentimentData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={sentimentData.map((item) => ({
                      name: SENTIMENT_LABELS[item.sentiment] || item.sentiment,
                      value: item.count,
                    }))}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    label={(props: PieLabelRenderProps) => `${String(props.name ?? '')} ${(((props.percent as number | undefined) ?? 0) * 100).toFixed(0)}%`}
                  >
                    {sentimentData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={SENTIMENT_COLORS[entry.sentiment] || '#8884d8'}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-60 items-center justify-center">
                <Text type="secondary">감성 분석 데이터가 없습니다</Text>
              </div>
            )}
          </Card>
        </Col>

        {/* Platform Trends Bar Chart */}
        <Col xs={24} lg={16}>
          <Card title="플랫폼별 성과" size="small">
            {platformTrends && platformTrends.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={platformTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="platform" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="views" name="조회수" fill="#1677ff" />
                  <Bar dataKey="likes" name="좋아요" fill="#52c41a" />
                  <Bar dataKey="shares" name="공유" fill="#faad14" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-60 items-center justify-center">
                <Text type="secondary">플랫폼 데이터가 없습니다</Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Recent Contents */}
        <Col xs={24} lg={12}>
          <Card title="최근 콘텐츠" size="small">
            <List
              dataSource={recentContents || []}
              locale={{ emptyText: '콘텐츠가 없습니다' }}
              renderItem={(item) => {
                const cfg = CONTENT_STATUS[item.status] || { color: 'default', text: item.status };
                return (
                  <List.Item>
                    <List.Item.Meta
                      title={item.title}
                      description={new Date(item.created_at).toLocaleString('ko-KR')}
                    />
                    <Tag color={cfg.color}>{cfg.text}</Tag>
                  </List.Item>
                );
              }}
            />
          </Card>
        </Col>

        {/* Today Schedule */}
        <Col xs={24} lg={6}>
          <Card title="오늘 예약" size="small">
            <List
              dataSource={todaySchedule || []}
              locale={{ emptyText: '예약된 콘텐츠가 없습니다' }}
              renderItem={(item) => (
                <List.Item>
                  <div>
                    <Text strong>{item.title}</Text>
                    <br />
                    <Text type="secondary" className="text-xs">
                      {new Date(item.scheduled_at).toLocaleTimeString('ko-KR')}
                    </Text>
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* Approval Status */}
        <Col xs={24} lg={6}>
          <Card title="승인 현황" size="small">
            <List
              dataSource={approvalStatus || []}
              locale={{ emptyText: '승인 데이터가 없습니다' }}
              renderItem={(item) => (
                <List.Item>
                  <Text>{STATUS_LABELS[item.status] || item.status}</Text>
                  <Tag>{item.count}건</Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
