/**
 * AI Dashboard Page — AI usage statistics and job history.
 * Shows token consumption, cost breakdown by task type, and recent AI jobs.
 */

import { useState } from 'react';
import {
  Alert,
  Card,
  Col,
  Empty,
  Progress,
  Row,
  Select,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Bot, Clock, Coins, Cpu, Zap } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import dayjs from 'dayjs';

import PageHeader from '@/shared/components/PageHeader';
import { useAiUsage, useAiJobs } from '../hooks/useAiUsage';
import type { AiJobListItem } from '../hooks/useAiUsage';

const { Text } = Typography;

const TASK_TYPE_LABELS: Record<string, string> = {
  TITLE: '제목 생성',
  DESCRIPTION: '설명 생성',
  HASHTAG: '해시태그',
  REPLY: '댓글 답글',
  TONE_TRANSFORM: '톤 변환',
  CONTENT_REVIEW: '콘텐츠 검수',
  SUGGEST_EFFECTS: '효과 제안',
  IMPROVE_TEMPLATE: '템플릿 개선',
  SUBTITLE: '자막 생성',
  SHORTFORM: '숏폼 추출',
  THUMBNAIL: '썸네일 생성',
  TRANSLATION: '번역',
  OPTIMAL_TIME: '최적 시간',
  SENTIMENT: '감성 분석',
};

const JOB_TYPE_LABELS: Record<string, string> = {
  SUBTITLE: '자막 생성',
  SHORTFORM: '숏폼 추출',
  THUMBNAIL: '썸네일 생성',
};

const JOB_STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  PENDING: { color: 'default', label: '대기 중' },
  PROCESSING: { color: 'processing', label: '처리 중' },
  COMPLETED: { color: 'success', label: '완료' },
  FAILED: { color: 'error', label: '실패' },
  CONFIRMED: { color: 'cyan', label: '확정' },
};

const PIE_COLORS = [
  '#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1',
  '#13c2c2', '#eb2f96', '#fa8c16', '#2f54eb', '#a0d911',
];

export default function AiDashboardPage() {
  const [jobPage, setJobPage] = useState(1);
  const [jobTypeFilter, setJobTypeFilter] = useState<string | undefined>();
  const [jobStatusFilter, setJobStatusFilter] = useState<string | undefined>();

  const { data: usage, isLoading: usageLoading, error: usageError } = useAiUsage();
  const { data: jobsData, isLoading: jobsLoading } = useAiJobs({
    page: jobPage,
    limit: 10,
    jobType: jobTypeFilter,
    status: jobStatusFilter,
  });

  const jobs = jobsData?.data ?? [];
  const jobsMeta = jobsData?.meta;

  // Pie chart data
  const pieData = (usage?.by_task_type ?? []).map((item) => ({
    name: TASK_TYPE_LABELS[item.task_type] ?? item.task_type,
    value: item.request_count,
  }));

  // Bar chart data (tokens)
  const barData = (usage?.by_task_type ?? [])
    .slice(0, 8)
    .map((item) => ({
      name: TASK_TYPE_LABELS[item.task_type] ?? item.task_type,
      tokens: item.total_tokens,
      cost: item.estimated_cost,
    }));

  const jobColumns: ColumnsType<AiJobListItem> = [
    {
      title: '작업 유형',
      dataIndex: 'job_type',
      key: 'job_type',
      width: 120,
      render: (type: string) => (
        <Tag icon={<Cpu size={12} />}>
          {JOB_TYPE_LABELS[type] ?? type}
        </Tag>
      ),
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const cfg = JOB_STATUS_CONFIG[s] ?? { color: 'default', label: s };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: '진행률',
      dataIndex: 'progress',
      key: 'progress',
      width: 140,
      render: (p: number, record: AiJobListItem) => (
        <Progress
          percent={p}
          size="small"
          status={record.status === 'FAILED' ? 'exception' : record.status === 'COMPLETED' ? 'success' : 'active'}
        />
      ),
    },
    {
      title: '생성일',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '완료일',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 160,
      render: (v: string | null) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '오류',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (v: string | null) => v ? <Text type="danger">{v}</Text> : '-',
    },
  ];

  if (usageLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  if (usageError) {
    return (
      <Alert
        type="error"
        message="AI 사용량 데이터를 불러오지 못했습니다."
        description="권한을 확인하거나 잠시 후 다시 시도해 주세요."
        showIcon
      />
    );
  }

  return (
    <div>
      <PageHeader
        title="AI 사용 현황"
        subtitle="AI 기능 사용량 통계 및 비동기 작업 이력"
      />

      {/* ── Summary Cards ── */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="총 요청 수"
              value={usage?.total_requests ?? 0}
              prefix={<Zap size={18} className="text-blue-500" />}
              suffix="건"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="총 토큰 사용량"
              value={usage?.total_tokens ?? 0}
              prefix={<Bot size={18} className="text-green-500" />}
              formatter={(v) => Number(v).toLocaleString()}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="예상 비용"
              value={usage?.estimated_cost ?? 0}
              prefix={<Coins size={18} className="text-yellow-500" />}
              precision={4}
              suffix="USD"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="작업 유형 수"
              value={(usage?.by_task_type ?? []).length}
              prefix={<Clock size={18} className="text-purple-500" />}
              suffix="종"
            />
          </Card>
        </Col>
      </Row>

      {/* ── Charts ── */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={12}>
          <Card title="작업 유형별 요청 분포">
            {pieData.length === 0 ? (
              <Empty description="아직 AI 사용 기록이 없습니다." />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, percent }) =>
                      `${name} ${(percent * 100).toFixed(0)}%`
                    }
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="작업 유형별 토큰 소비">
            {barData.length === 0 ? (
              <Empty description="아직 AI 사용 기록이 없습니다." />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis />
                  <Tooltip
                    formatter={(value: number) => value.toLocaleString()}
                  />
                  <Bar dataKey="tokens" fill="#1677ff" name="토큰" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      {/* ── Job History Table ── */}
      <Card
        title="AI 작업 이력"
        extra={
          <div className="flex gap-2">
            <Select
              placeholder="작업 유형"
              allowClear
              style={{ width: 140 }}
              value={jobTypeFilter}
              onChange={setJobTypeFilter}
              options={[
                { label: '자막 생성', value: 'SUBTITLE' },
                { label: '숏폼 추출', value: 'SHORTFORM' },
                { label: '썸네일 생성', value: 'THUMBNAIL' },
              ]}
            />
            <Select
              placeholder="상태"
              allowClear
              style={{ width: 120 }}
              value={jobStatusFilter}
              onChange={setJobStatusFilter}
              options={[
                { label: '대기 중', value: 'PENDING' },
                { label: '처리 중', value: 'PROCESSING' },
                { label: '완료', value: 'COMPLETED' },
                { label: '실패', value: 'FAILED' },
                { label: '확정', value: 'CONFIRMED' },
              ]}
            />
          </div>
        }
      >
        <Table<AiJobListItem>
          dataSource={jobs}
          columns={jobColumns}
          rowKey="job_id"
          loading={jobsLoading}
          pagination={{
            current: jobPage,
            pageSize: 10,
            total: jobsMeta?.total ?? 0,
            onChange: setJobPage,
            showSizeChanger: false,
            showTotal: (total) => `총 ${total}건`,
          }}
          locale={{ emptyText: <Empty description="AI 작업 이력이 없습니다." /> }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  );
}
