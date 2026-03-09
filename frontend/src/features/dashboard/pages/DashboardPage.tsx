import { Card, Col, List, Radio, Row, Select, Spin, Statistic, Table, Tag, Typography } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { PlatformTrendChart, SentimentPieChart } from '@/shared/components/charts';
import type { MetricKey } from '@/shared/components/charts';
import { APPROVAL_STATUS_CONFIG, getStatusConfig } from '@/shared/constants/contentStatus';
import { getPlatformConfig } from '@/shared/constants/platform';
import { useAuthStore } from '@/shared/stores/useAuthStore';

import {
  useAllOrganizations,
  useApprovalStatus,
  useDashboardSummary,
  usePlatformTrends,
  useRecentContents,
  useSentimentSummary,
  useTodaySchedule,
} from '../hooks/useDashboard';
import type { OrgSummaryItem } from '../hooks/useDashboard';

const { Title, Text } = Typography;

type MetricFilter = 'all' | MetricKey;

export default function DashboardPage() {
  const navigate = useNavigate();
  const userRole = useAuthStore((s) => s.user?.role);
  const [selectedMetric, setSelectedMetric] = useState<MetricFilter>('all');
  const [period, setPeriod] = useState('7d');
  const { data: summary, isLoading } = useDashboardSummary(period);
  const { data: recentContents } = useRecentContents();
  const { data: todaySchedule } = useTodaySchedule();
  const { data: approvalStatus } = useApprovalStatus();
  const { data: sentimentData } = useSentimentSummary(period);
  const { data: platformTrends } = usePlatformTrends(period);
  const isAM = userRole === 'AGENCY_MANAGER' || userRole === 'SYSTEM_ADMIN';
  const { data: allOrgs, isLoading: isOrgsLoading } = useAllOrganizations(isAM);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  const dangerousCount = sentimentData?.find((s) => s.sentiment === 'DANGEROUS')?.count ?? 0;

  const visibleMetrics: MetricKey[] =
    selectedMetric === 'all' ? ['views', 'likes', 'shares'] : [selectedMetric];

  /* ── Approval Card (shared between CD prominent & normal positions) ── */
  const approvalCard = (
    <Card title="승인 대기 현황" size="small">
      <List
        dataSource={approvalStatus || []}
        locale={{ emptyText: '승인 데이터가 없습니다' }}
        renderItem={(item) => (
          <List.Item>
            <Text>- {APPROVAL_STATUS_CONFIG[item.status]?.text || item.status}</Text>
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
          value={period}
          onChange={setPeriod}
          style={{ width: 120 }}
          options={[
            { value: '7d', label: '최근 7일' },
            { value: '30d', label: '최근 30일' },
          ]}
        />
      </div>

      {/* AM role: org comparison table */}
      {isAM && (
        <Card title="기관별 현황 비교" size="small" className="mb-4">
          <Table<OrgSummaryItem>
            rowKey="id"
            loading={isOrgsLoading}
            dataSource={allOrgs || []}
            pagination={false}
            size="small"
            locale={{ emptyText: '기관 데이터가 없습니다' }}
            columns={[
              { title: '기관명', dataIndex: 'name', key: 'name', render: (name: string) => <Text strong>{name}</Text> },
              { title: '전체 콘텐츠', dataIndex: 'total_contents', key: 'total_contents', align: 'right' },
              { title: '게시 완료', dataIndex: 'published_contents', key: 'published_contents', align: 'right' },
              { title: '활성 채널', dataIndex: 'active_channels', key: 'active_channels', align: 'right' },
              {
                title: '대기 승인',
                dataIndex: 'pending_approvals',
                key: 'pending_approvals',
                align: 'right',
                render: (v: number) => v > 0 ? <Text type="warning">{v}건</Text> : <Text type="secondary">0건</Text>,
              },
            ]}
          />
        </Card>
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
              title="총 도달"
              value={summary?.total_views ?? 0}
              valueStyle={{ fontSize: 28 }}
            />
            {summary?.views_growth != null && (
              <Text type={summary.views_growth >= 0 ? 'success' : 'danger'} className="text-xs">
                {summary.views_growth >= 0 ? '+' : ''}{summary.views_growth.toFixed(1)}%
              </Text>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="총 게시물"
              value={summary?.total_contents ?? 0}
              valueStyle={{ fontSize: 28 }}
            />
            {summary?.contents_growth != null ? (
              <Text type={summary.contents_growth >= 0 ? 'success' : 'danger'} className="text-xs">
                {summary.contents_growth >= 0 ? '+' : ''}{summary.contents_growth.toFixed(1)}%
              </Text>
            ) : (
              <Text type="secondary" className="text-xs">게시 {summary?.published_contents ?? 0}건</Text>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="총 댓글"
              value={summary?.total_comments ?? sentimentData?.reduce((sum, s) => sum + s.count, 0) ?? 0}
              valueStyle={{ fontSize: 28 }}
            />
            {summary?.comments_growth != null && (
              <Text type={summary.comments_growth >= 0 ? 'success' : 'danger'} className="text-xs">
                {summary.comments_growth >= 0 ? '+' : ''}{summary.comments_growth.toFixed(1)}%
              </Text>
            )}
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
                onChange={(e) => setSelectedMetric(e.target.value as MetricFilter)}
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
            <PlatformTrendChart data={platformTrends || []} visibleMetrics={visibleMetrics} />
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
                  const cfg = getStatusConfig(item.status);
                  const platform = item.platforms?.[0];
                  const pcfg = platform ? getPlatformConfig(platform) : null;
                  return (
                    <List.Item
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => navigate(`/contents/${item.id}`)}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1">
                          {pcfg && <Tag color={pcfg.color} className="!text-xs">[{pcfg.short}]</Tag>}
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
            <SentimentPieChart data={sentimentData || []} />
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
                  const cfg = getStatusConfig(item.status);
                  const platform = item.platforms?.[0];
                  const pcfg = platform ? getPlatformConfig(platform) : null;
                  return (
                    <List.Item
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => navigate(`/contents/${item.id}`)}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1">
                          {pcfg && <Tag color={pcfg.color} className="!text-xs">[{pcfg.short}]</Tag>}
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
            const cfg = getStatusConfig(item.status);
            const statusColor = item.status === 'PUBLISHED' ? '#52c41a' : item.status === 'PENDING_REVIEW' ? '#faad14' : '#1677ff';
            const statusIcon = item.status === 'PUBLISHED' ? '●' : item.status === 'PENDING_REVIEW' ? '◐' : '○';
            const platform = item.platforms?.[0];
            const pcfg = platform ? getPlatformConfig(platform) : null;
            return (
              <List.Item
                className="cursor-pointer hover:bg-gray-50"
                onClick={() => navigate(`/contents/${item.id}`)}
              >
                <div className="flex items-center gap-3">
                  <Text className="w-12 font-mono text-sm">{time}</Text>
                  {pcfg && <Tag color={pcfg.color}>{pcfg.short}</Tag>}
                  <Text className="text-sm">{item.title}</Text>
                  <span style={{ color: statusColor }}>{statusIcon} {cfg.text}</span>
                </div>
              </List.Item>
            );
          }}
        />
      </Card>
    </div>
  );
}
