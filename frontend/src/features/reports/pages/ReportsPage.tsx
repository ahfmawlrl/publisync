import { useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Drawer,
  Tag,
  Badge,
  DatePicker,
  Radio,
  Space,
  message,
  Spin,
  Card,
  Typography,
  Descriptions,
  Empty,
  Segmented,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { FileText, Download, Plus, CheckCircle } from 'lucide-react';
import dayjs from 'dayjs';

import {
  useReportsList,
  useGenerateReport,
  useReport,
  useFinalizeReport,
} from '../hooks/useReports';
import type { GenerateReportRequest, Report, ReportListItem } from '../types';
import apiClient from '@/shared/api/client';

const { Title, Paragraph, Text } = Typography;
const { RangePicker } = DatePicker;

const PERIOD_LABELS: Record<string, string> = {
  WEEKLY: '주간',
  MONTHLY: '월간',
  QUARTERLY: '분기',
};

const PERIOD_COLORS: Record<string, string> = {
  WEEKLY: 'blue',
  MONTHLY: 'green',
  QUARTERLY: 'purple',
};

const STATUS_MAP: Record<string, { status: 'processing' | 'default' | 'success'; text: string }> = {
  GENERATING: { status: 'processing', text: '생성중' },
  DRAFT: { status: 'default', text: '초안' },
  FINALIZED: { status: 'success', text: '확정' },
};

const SECTION_TITLES: Record<string, string> = {
  summary: '요약',
  platformPerformance: '플랫폼별 성과',
  topContents: '주요 콘텐츠',
  commentAnalysis: '댓글/여론 분석',
  aiSuggestions: '개선 제안',
};

export default function ReportsPage() {
  const [filters, setFilters] = useState<{ period?: string; status?: string; page?: number }>({});
  const [generateModal, setGenerateModal] = useState(false);
  const [detailDrawer, setDetailDrawer] = useState<string | null>(null);
  const [genForm, setGenForm] = useState<{
    period: string;
    range: [dayjs.Dayjs, dayjs.Dayjs] | null;
  }>({ period: 'MONTHLY', range: null });
  const [polling, setPolling] = useState<string | null>(null);

  const { data: reportsList, isLoading } = useReportsList(filters);
  const { data: selectedReport, isLoading: isDetailLoading } = useReport(detailDrawer ?? undefined);
  const generateMutation = useGenerateReport();
  const finalizeMutation = useFinalizeReport();

  // Poll job status
  const pollJobStatus = async (jobId: string) => {
    setPolling(jobId);
    const maxAttempts = 60;
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((r) => setTimeout(r, 3000));
      try {
        const res = await apiClient.get(`/ai/jobs/${jobId}`);
        const job = (res.data as { data: { status: string } }).data;
        if (job.status === 'COMPLETED') {
          message.success('리포트가 생성되었습니다.');
          setPolling(null);
          return;
        }
        if (job.status === 'FAILED') {
          message.error('리포트 생성에 실패했습니다.');
          setPolling(null);
          return;
        }
      } catch {
        // continue polling
      }
    }
    message.warning('리포트 생성이 지연되고 있습니다. 목록에서 확인해주세요.');
    setPolling(null);
  };

  const handleGenerate = async () => {
    if (!genForm.range) {
      message.warning('기간을 선택해주세요.');
      return;
    }
    try {
      const body: GenerateReportRequest = {
        period: genForm.period,
        period_start: genForm.range[0].format('YYYY-MM-DD'),
        period_end: genForm.range[1].format('YYYY-MM-DD'),
      };
      const result = await generateMutation.mutateAsync(body);
      setGenerateModal(false);
      message.info('리포트 생성이 시작되었습니다.');
      if (result?.job_id) {
        pollJobStatus(result.job_id);
      }
    } catch {
      message.error('리포트 생성 요청에 실패했습니다.');
    }
  };

  const handleFinalize = async (id: string) => {
    try {
      await finalizeMutation.mutateAsync(id);
      message.success('리포트가 확정되었습니다.');
    } catch {
      message.error('리포트 확정에 실패했습니다.');
    }
  };

  const handleDownload = (id: string) => {
    const url = `/api/v1/reports/${id}/download`;
    window.open(url, '_blank');
  };

  const columns: ColumnsType<ReportListItem> = [
    {
      title: '제목',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (val: string, record) => (
        <Button type="link" onClick={() => setDetailDrawer(record.id)} className="!p-0">
          {val}
        </Button>
      ),
    },
    {
      title: '유형',
      dataIndex: 'period',
      key: 'period',
      width: 100,
      render: (val: string) => (
        <Tag color={PERIOD_COLORS[val] ?? 'default'}>{PERIOD_LABELS[val] ?? val}</Tag>
      ),
    },
    {
      title: '기간',
      key: 'period_range',
      width: 200,
      render: (_, record) => `${record.period_start} ~ ${record.period_end}`,
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (val: string) => {
        const info = STATUS_MAP[val] ?? { status: 'default' as const, text: val };
        return <Badge status={info.status} text={info.text} />;
      },
    },
    {
      title: '생성일',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<FileText size={14} />}
            onClick={() => setDetailDrawer(record.id)}
          >
            상세
          </Button>
          {record.status === 'FINALIZED' && (
            <Button
              size="small"
              icon={<Download size={14} />}
              onClick={() => handleDownload(record.id)}
            />
          )}
        </Space>
      ),
    },
  ];

  const renderSectionContent = (key: string, section: Report['content'][string]) => {
    if (!section) return null;
    if (section.type === 'AI_TEXT') {
      return (
        <Card key={key} title={SECTION_TITLES[key] ?? key} className="mb-4">
          <Paragraph>{section.content}</Paragraph>
        </Card>
      );
    }
    if (section.type === 'CHART_DATA') {
      return (
        <Card key={key} title={SECTION_TITLES[key] ?? key} className="mb-4">
          <Paragraph>{section.content}</Paragraph>
          {section.data != null && (
            <pre className="mt-2 rounded bg-gray-50 p-3 text-sm">
              {JSON.stringify(section.data, null, 2)}
            </pre>
          )}
        </Card>
      );
    }
    if (section.type === 'TABLE_DATA') {
      const tableData = Array.isArray(section.data) ? section.data : [];
      return (
        <Card key={key} title={SECTION_TITLES[key] ?? key} className="mb-4">
          <Paragraph>{section.content}</Paragraph>
          {tableData.length > 0 && (
            <Table
              rowKey={(_, idx) => String(idx)}
              dataSource={tableData}
              columns={Object.keys(tableData[0] ?? {}).map((col) => ({
                title: col,
                dataIndex: col,
                key: col,
              }))}
              pagination={false}
              size="small"
            />
          )}
        </Card>
      );
    }
    return null;
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          운영 리포트
        </Title>
        <Space>
          {polling && <Spin size="small" />}
          <Button type="primary" icon={<Plus size={16} />} onClick={() => setGenerateModal(true)}>
            새 리포트 생성
          </Button>
        </Space>
      </div>

      {/* Filters */}
      <div className="mb-4 flex items-center gap-3">
        <Segmented
          options={[
            { label: '전체', value: '' },
            { label: '주간', value: 'WEEKLY' },
            { label: '월간', value: 'MONTHLY' },
            { label: '분기', value: 'QUARTERLY' },
          ]}
          value={filters.period ?? ''}
          onChange={(val) => setFilters((p) => ({ ...p, period: val as string || undefined, page: 1 }))}
        />
        <Segmented
          options={[
            { label: '전체', value: '' },
            { label: '초안', value: 'DRAFT' },
            { label: '확정', value: 'FINALIZED' },
          ]}
          value={filters.status ?? ''}
          onChange={(val) => setFilters((p) => ({ ...p, status: val as string || undefined, page: 1 }))}
        />
      </div>

      {/* Table */}
      <Table<ReportListItem>
        rowKey="id"
        columns={columns}
        dataSource={reportsList?.data ?? []}
        loading={isLoading}
        pagination={{
          current: filters.page ?? 1,
          total: reportsList?.meta?.total ?? 0,
          pageSize: 20,
          onChange: (page) => setFilters((p) => ({ ...p, page })),
          showSizeChanger: false,
        }}
        locale={{ emptyText: <Empty description="리포트가 없습니다" /> }}
      />

      {/* Generate Modal */}
      <Modal
        title="AI 리포트 생성"
        open={generateModal}
        onCancel={() => setGenerateModal(false)}
        onOk={handleGenerate}
        okText="AI 생성 시작"
        confirmLoading={generateMutation.isPending}
      >
        <div className="space-y-4 py-2">
          <div>
            <Text strong className="mb-2 block">
              리포트 유형
            </Text>
            <Radio.Group
              value={genForm.period}
              onChange={(e) => setGenForm((p) => ({ ...p, period: e.target.value }))}
            >
              <Radio.Button value="WEEKLY">주간</Radio.Button>
              <Radio.Button value="MONTHLY">월간</Radio.Button>
              <Radio.Button value="QUARTERLY">분기</Radio.Button>
            </Radio.Group>
          </div>
          <div>
            <Text strong className="mb-2 block">
              분석 기간
            </Text>
            <RangePicker
              value={genForm.range}
              onChange={(dates) =>
                setGenForm((p) => ({
                  ...p,
                  range: dates as [dayjs.Dayjs, dayjs.Dayjs] | null,
                }))
              }
              className="w-full"
            />
          </div>
          <Paragraph type="secondary">
            선택한 기간의 성과 데이터를 AI가 분석하여 리포트를 자동 생성합니다.
            생성에 1~3분 정도 소요됩니다.
          </Paragraph>
        </div>
      </Modal>

      {/* Detail Drawer */}
      <Drawer
        title={selectedReport?.title ?? '리포트 상세'}
        open={!!detailDrawer}
        onClose={() => setDetailDrawer(null)}
        width={720}
        extra={
          selectedReport && (
            <Space>
              {selectedReport.status === 'DRAFT' && (
                <Button
                  type="primary"
                  icon={<CheckCircle size={14} />}
                  onClick={() => handleFinalize(selectedReport.id)}
                  loading={finalizeMutation.isPending}
                >
                  확정
                </Button>
              )}
              {selectedReport.pdf_url && (
                <Button
                  icon={<Download size={14} />}
                  onClick={() => handleDownload(selectedReport.id)}
                >
                  PDF 다운로드
                </Button>
              )}
            </Space>
          )
        }
      >
        {isDetailLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Spin size="large" />
          </div>
        ) : selectedReport ? (
          <div>
            <Descriptions column={2} className="mb-6" bordered size="small">
              <Descriptions.Item label="유형">
                <Tag color={PERIOD_COLORS[selectedReport.period] ?? 'default'}>
                  {PERIOD_LABELS[selectedReport.period] ?? selectedReport.period}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="상태">
                <Badge
                  status={STATUS_MAP[selectedReport.status]?.status ?? 'default'}
                  text={STATUS_MAP[selectedReport.status]?.text ?? selectedReport.status}
                />
              </Descriptions.Item>
              <Descriptions.Item label="분석 기간">
                {selectedReport.period_start} ~ {selectedReport.period_end}
              </Descriptions.Item>
              <Descriptions.Item label="생성일">
                {dayjs(selectedReport.created_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
              {selectedReport.generated_by && (
                <Descriptions.Item label="AI 모델">
                  {selectedReport.generated_by}
                </Descriptions.Item>
              )}
              {selectedReport.finalized_at && (
                <Descriptions.Item label="확정일">
                  {dayjs(selectedReport.finalized_at).format('YYYY-MM-DD HH:mm')}
                </Descriptions.Item>
              )}
            </Descriptions>

            {/* Report sections */}
            {selectedReport.content && Object.keys(selectedReport.content).length > 0 ? (
              Object.entries(selectedReport.content).map(([key, section]) =>
                renderSectionContent(key, section),
              )
            ) : (
              <Empty description="리포트 내용이 없습니다" />
            )}
          </div>
        ) : (
          <Empty description="리포트를 찾을 수 없습니다" />
        )}
      </Drawer>
    </div>
  );
}
