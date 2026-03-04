/**
 * AI Job progress tracking component — S18 (F03/F15).
 *
 * Displays real-time progress for async AI jobs (subtitle generation,
 * shortform extraction) with status indicators and result preview.
 */

import { Alert, Button, Card, Progress, Space, Tag, Typography } from 'antd';
import { CheckCircle, Clock, Loader, XCircle } from 'lucide-react';

import { useJobStatus } from '../hooks/useAiJobs';

const { Text } = Typography;

const STATUS_CONFIG = {
  PENDING: { color: 'default' as const, icon: <Clock size={16} />, label: '대기 중' },
  PROCESSING: { color: 'processing' as const, icon: <Loader size={16} />, label: '처리 중' },
  COMPLETED: { color: 'success' as const, icon: <CheckCircle size={16} />, label: '완료' },
  FAILED: { color: 'error' as const, icon: <XCircle size={16} />, label: '실패' },
};

const JOB_TYPE_LABELS: Record<string, string> = {
  SUBTITLE: '자막 생성',
  SHORTFORM: '숏폼 추출',
};

interface AiJobProgressProps {
  jobId: string | null;
  title?: string;
  onComplete?: (result: Record<string, unknown>) => void;
  onClose?: () => void;
}

export default function AiJobProgress({
  jobId,
  title = 'AI 작업 진행 상황',
  onComplete,
  onClose,
}: AiJobProgressProps) {
  const { data: job, isLoading } = useJobStatus(jobId);

  if (!jobId || isLoading) return null;

  if (!job) {
    return <Alert type="warning" message="작업 정보를 불러올 수 없습니다." />;
  }

  const config = STATUS_CONFIG[job.status] || STATUS_CONFIG.PENDING;

  // Trigger onComplete callback
  if (job.status === 'COMPLETED' && job.result && onComplete) {
    onComplete(job.result);
  }

  const progressStatus =
    job.status === 'FAILED'
      ? 'exception'
      : job.status === 'COMPLETED'
        ? 'success'
        : 'active';

  return (
    <Card
      size="small"
      title={
        <Space>
          {config.icon}
          <span>{title}</span>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <Tag color={config.color}>{config.label}</Tag>
          <Text type="secondary">
            {JOB_TYPE_LABELS[job.job_type] ?? job.job_type}
          </Text>
        </Space>

        <Progress percent={job.progress} status={progressStatus} />

        {job.error_message && (
          <Alert type="error" message={job.error_message} showIcon />
        )}

        {job.status === 'COMPLETED' && job.result && (
          <Alert
            type="success"
            message="작업이 완료되었습니다."
            description={`결과: ${JSON.stringify(job.result).substring(0, 200)}...`}
            showIcon
          />
        )}

        {onClose && (
          <Button size="small" onClick={onClose}>
            닫기
          </Button>
        )}
      </Space>
    </Card>
  );
}
