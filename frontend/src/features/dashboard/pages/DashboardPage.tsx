import { Alert, Card, Col, List, Radio, Row, Select, Spin, Statistic, Tag, Typography } from 'antd';
import type { PieLabelRenderProps } from 'recharts';
import { CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { useAuthStore } from '@/shared/stores/useAuthStore';

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
  PENDING_REVIEW: '검수 대기',
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

const PLATFORM_TAG: Record<string, { color: string; label: string }> = {
  YOUTUBE: { color: 'red', label: 'YT' },
  INSTAGRAM: { color: 'green', label: 'IG' },
  FACEBOOK: { color: 'blue', label: 'FB' },
  X: { color: 'default', label: 'X' },
  NAVER_BLOG: { color: 'green', label: 'Blog' },
};

type MetricKey = 'all' | 'views' | 'likes' | 'shares';

const METRIC_LINE_CONFIG: Record<Exclude<MetricKey, 'all'>, { name: string; color: string }> = {
  views: { name: '조회수', color: '#1677ff' },
  likes: { name: '좋아요', color: '#52c41a' },
  shares: { name: '공유', color: '#faad14' },
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const userRole = useAuthStore((s) => s.user?.role);
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>('all');
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

  const dangerousCount = sentimentData?.find((s) => s.sentiment === 'DANGEROUS')?.count ?? 0;

  const visibleMetrics: Array<Exclude<MetricKey, 'all'>> =
    selectedMetric === 'all' ? ['views', 'likes', 'shares'] : [selectedMetric];

  /* ── Approval Card (shared between CD prominent & normal positions) ── */
  const approvalCard = (
    <Card title="승인 대기 현황" size="small">
      <List
        dataSource={approvalStatus || []}
        locale={{ emptyText: '승인 데이터가 없습니다' }}
        renderItem={(item) => (
          <List.Item>
            <Text>- {STATUS_LABELS[item.status] || item.status}</Text>
            <Text strong>{item.count}건</Text>
          </List.Item>
        )}
      />
      <div className="mt-3">
        <a onClick={() => navigate('/approvals')}>승인 대기 목록 보기 &rarr;</a>
      </div>
    </Card>
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">대시보드</Title>
        <Select
          defaultValue="7d"
          style={{ width: 120 }}
          options={[
            { value: '7d', label: '최근 7일' },
            { value: '30d', label: '최근 30일' },
          ]}
        />
      </div>

      {/* AM role: full-org comparison note */}
      {userRole === 'AGENCY_MANAGER' && (
        <Alert
          type="info"
          showIcon
          message="전체 기관 비교 뷰는 Phase 1-B에서 지원됩니다"
          className="mb-4"
        />
      )}

      {/* CD role: Prominent approval card at the TOP */}
      {userRole === 'CLIENT_DIRECTOR' && (
        <div className="mb-6" style={{ border: '2px solid #1677ff', borderRadius: 8 }}>
          {approvalCard}
        </div>
      )}

      {/* KPI Cards — 4 cards matching prototype */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="총 팔로워"
              value={summary?.total_views ?? 0}
              valueStyle={{ fontSize: 28 }}
            />
            <Text type="success" className="text-xs">+3.2%</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="총 게시물"
              value={summary?.total_contents ?? 0}
              valueStyle={{ fontSize: 28 }}
            />
            <Text type="success" className="text-xs">+{summary?.published_contents ?? 0}건</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="총 댓글"
              value={sentimentData?.reduce((sum, s) => sum + s.count, 0) ?? 0}
              valueStyle={{ fontSize: 28 }}
            />
            <Text type="success" className="text-xs">+18%</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            className="cursor-pointer transition-shadow hover:shadow-md"
            onClick={() => navigate('/comments/dangerous')}
          >
            <Statistic
              title="위험 댓글"
              value={dangerousCount}
              valueStyle={{ fontSize: 28, color: '#ff4d4f' }}
            />
            <Text style={{ color: '#ff4d4f' }} className="text-xs">즉시 확인</Text>
          </Card>
        </Col>
      </Row>

      {/* Row 2: Platform trends (LineChart) + Approval status */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={12}>
          <Card
            title="플랫폼별 성과 추이"
            size="small"
            extra={
              <Radio.Group
                size="small"
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value as MetricKey)}
                optionType="button"
                buttonStyle="solid"
              >
                <Radio.Button value="all">전체</Radio.Button>
                <Radio.Button value="views">조회수</Radio.Button>
                <Radio.Button value="likes">좋아요</Radio.Button>
                <Radio.Button value="shares">공유</Radio.Button>
              </Radio.Group>
            }
          >
            {platformTrends && platformTrends.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={platformTrends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="platform" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {visibleMetrics.map((key) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      name={METRIC_LINE_CONFIG[key].name}
                      stroke={METRIC_LINE_CONFIG[key].color}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-60 items-center justify-center">
                <Text type="secondary">플랫폼 데이터가 없습니다</Text>
              </div>
            )}
          </Card>
        </Col>
        {/* Show approval card in normal position for non-CD roles */}
        {userRole !== 'CLIENT_DIRECTOR' && (
          <Col xs={24} lg={12}>
            {approvalCard}
          </Col>
        )}
        {/* CD role: show recent contents here instead since approval is at top */}
        {userRole === 'CLIENT_DIRECTOR' && (
          <Col xs={24} lg={12}>
            <Card title="최근 게시 콘텐츠" size="small">
              <List
                dataSource={recentContents || []}
                locale={{ emptyText: '콘텐츠가 없습니다' }}
                renderItem={(item) => {
                  const cfg = CONTENT_STATUS[item.status] || { color: 'default', text: item.status };
                  const platform = item.platforms?.[0];
                  const ptag = platform ? PLATFORM_TAG[platform] : null;
                  return (
                    <List.Item>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1">
                          {ptag && <Tag color={ptag.color} className="!text-xs">[{ptag.label}]</Tag>}
                          <Text strong className="truncate text-sm">{item.title}</Text>
                        </div>
                      </div>
                      <Tag color={cfg.color}>{cfg.text}</Tag>
                    </List.Item>
                  );
                }}
              />
            </Card>
          </Col>
        )}
      </Row>

      {/* Row 3: Sentiment donut + Recent contents (non-CD) */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={12}>
          <Card title="댓글 감성 분석 현황" size="small">
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
        {/* For non-CD roles, show recent contents here (CD already has it in Row 2) */}
        {userRole !== 'CLIENT_DIRECTOR' && (
          <Col xs={24} lg={12}>
            <Card title="최근 게시 콘텐츠" size="small">
              <List
                dataSource={recentContents || []}
                locale={{ emptyText: '콘텐츠가 없습니다' }}
                renderItem={(item) => {
                  const cfg = CONTENT_STATUS[item.status] || { color: 'default', text: item.status };
                  const platform = item.platforms?.[0];
                  const ptag = platform ? PLATFORM_TAG[platform] : null;
                  return (
                    <List.Item>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1">
                          {ptag && <Tag color={ptag.color} className="!text-xs">[{ptag.label}]</Tag>}
                          <Text strong className="truncate text-sm">{item.title}</Text>
                        </div>
                      </div>
                      <Tag color={cfg.color}>{cfg.text}</Tag>
                    </List.Item>
                  );
                }}
              />
            </Card>
          </Col>
        )}
      </Row>

      {/* Row 4: Today schedule */}
      <Card title="오늘의 게시 일정" size="small">
        <List
          dataSource={todaySchedule || []}
          locale={{ emptyText: '예약된 콘텐츠가 없습니다' }}
          renderItem={(item) => {
            const time = new Date(item.scheduled_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
            const statusText = CONTENT_STATUS[item.status]?.text || item.status;
            const statusColor = item.status === 'PUBLISHED' ? '#52c41a' : item.status === 'PENDING_REVIEW' ? '#faad14' : '#1677ff';
            const statusIcon = item.status === 'PUBLISHED' ? '●' : item.status === 'PENDING_REVIEW' ? '◐' : '○';
            const platform = item.platforms?.[0];
            const ptag = platform ? PLATFORM_TAG[platform] : null;
            return (
              <List.Item>
                <div className="flex items-center gap-3">
                  <Text className="w-12 font-mono text-sm">{time}</Text>
                  {ptag && <Tag color={ptag.color}>{ptag.label}</Tag>}
                  <Text className="text-sm">{item.title}</Text>
                  <span style={{ color: statusColor }}>{statusIcon} {statusText}</span>
                </div>
              </List.Item>
            );
          }}
        />
        <div className="mt-3 text-[11px] text-gray-400">
          데이터 최신성: YouTube 2분 전 · Instagram 5분 전
        </div>
      </Card>
    </div>
  );
}
