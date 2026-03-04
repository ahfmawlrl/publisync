/**
 * Shortform Editor Page -- S18 (F15).
 *
 * Two-column layout:
 *   Left (60%): VideoPlayer for preview
 *   Right (40%): Clip list with AI-suggested segments + controls
 *
 * Workflow: Load asset -> AI extract segments -> Review / Select -> Confirm
 */

import { CheckOutlined, PlayCircleOutlined } from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  Checkbox,
  Empty,
  List,
  Modal,
  Space,
  Tag,
  Typography,
} from 'antd';
import { useCallback, useRef, useState } from 'react';
import { useParams } from 'react-router';

import VideoPlayer from '@/shared/components/VideoPlayer';

import AiJobProgress from '../components/AiJobProgress';
import { useCreateShortform } from '../hooks/useAiJobs';

const { Title, Text } = Typography;

// ── Types ───────────────────────────────────────────────

interface ClipSegment {
  id: string;
  start: number; // seconds
  end: number;
  label: string;
  selected: boolean;
}

// ── Helpers ─────────────────────────────────────────────

/** Format seconds as MM:SS. */
function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/** Format duration in seconds. */
function formatDuration(start: number, end: number): string {
  const duration = Math.max(0, end - start);
  if (duration < 60) return `${duration.toFixed(1)}초`;
  return `${Math.floor(duration / 60)}분 ${Math.floor(duration % 60)}초`;
}

// ── Component ───────────────────────────────────────────

export default function ShortformEditorPage() {
  const { assetId } = useParams<{ assetId: string }>();
  const { message } = App.useApp();

  // AI job state
  const [jobId, setJobId] = useState<string | null>(null);
  const createShortformMutation = useCreateShortform();

  // Clip segments
  const [clips, setClips] = useState<ClipSegment[]>([]);

  // Video player ref for seeking
  const videoPlayerRef = useRef<{ seekTo?: (time: number) => void }>(null);

  // Ref for tracking whether result was already consumed
  const resultConsumedRef = useRef(false);

  // Summary modal
  const [summaryOpen, setSummaryOpen] = useState(false);

  // ── Handlers ────────────────────────────────────────

  const handleExtractShortform = useCallback(() => {
    if (!assetId) return;
    resultConsumedRef.current = false;
    createShortformMutation.mutate(
      { media_asset_id: assetId },
      {
        onSuccess: (data) => {
          setJobId(data.job_id);
          message.info('AI 구간 추출 작업을 시작했습니다.');
        },
        onError: () => message.error('AI 구간 추출 요청에 실패했습니다.'),
      },
    );
  }, [assetId, createShortformMutation, message]);

  const handleJobComplete = useCallback(
    (result: Record<string, unknown>) => {
      if (resultConsumedRef.current) return;
      resultConsumedRef.current = true;

      // Expect result.clips to be an array of segments
      const raw = result.clips;
      if (Array.isArray(raw)) {
        const parsed: ClipSegment[] = raw.map(
          (item: Record<string, unknown>, idx: number) => ({
            id: String(item.id ?? `clip-${idx + 1}`),
            start: Number(item.start ?? 0),
            end: Number(item.end ?? 0),
            label: String(item.label ?? `구간 ${idx + 1}`),
            selected: true,
          }),
        );
        setClips(parsed);
        message.success(`${parsed.length}개 구간이 추출되었습니다.`);
      } else {
        message.warning('구간 결과를 파싱할 수 없습니다. 수동으로 입력해주세요.');
      }
    },
    [message],
  );

  const handleToggleSelect = useCallback((clipId: string) => {
    setClips((prev) =>
      prev.map((clip) =>
        clip.id === clipId ? { ...clip, selected: !clip.selected } : clip,
      ),
    );
  }, []);

  const handlePreviewClip = useCallback(
    (clip: ClipSegment) => {
      if (videoPlayerRef.current?.seekTo) {
        videoPlayerRef.current.seekTo(clip.start);
        message.info(`${formatTime(clip.start)}부터 재생합니다.`);
      }
    },
    [message],
  );

  const handleShowSummary = useCallback(() => {
    const selected = clips.filter((c) => c.selected);
    if (selected.length === 0) {
      message.warning('선택된 구간이 없습니다.');
      return;
    }
    setSummaryOpen(true);
  }, [clips, message]);

  const handleCloseJobProgress = useCallback(() => {
    setJobId(null);
  }, []);

  // ── Derived state ───────────────────────────────────

  const selectedClips = clips.filter((c) => c.selected);
  const totalSelectedDuration = selectedClips.reduce(
    (acc, clip) => acc + Math.max(0, clip.end - clip.start),
    0,
  );

  // ── Render ──────────────────────────────────────────

  if (!assetId) {
    return (
      <div className="p-6">
        <Title level={4}>미디어 자산 ID가 필요합니다</Title>
      </div>
    );
  }

  const isJobRunning = !!jobId;
  const isExtracting = createShortformMutation.isPending;

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          숏폼 편집기
        </Title>
        <Space>
          <Button
            type="primary"
            onClick={handleExtractShortform}
            loading={isExtracting}
            disabled={isJobRunning}
          >
            AI 구간 추출
          </Button>
          <Button
            icon={<CheckOutlined />}
            onClick={handleShowSummary}
            disabled={selectedClips.length === 0}
          >
            선택한 구간 확인
          </Button>
        </Space>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        {/* Left column: Video Player (60%) */}
        <div className="lg:col-span-3">
          <Card size="small" title="미리보기">
            <VideoPlayer src={`/api/v1/media/${assetId}/download`} />
          </Card>
        </div>

        {/* Right column: Clip list (40%) */}
        <div className="space-y-4 lg:col-span-2">
          {/* AI Job Progress */}
          {isJobRunning && (
            <AiJobProgress
              jobId={jobId}
              title="AI 구간 추출"
              onComplete={handleJobComplete}
              onClose={handleCloseJobProgress}
            />
          )}

          {/* Clip list */}
          <Card
            size="small"
            title={
              <Space>
                <span>추출 구간</span>
                <Text type="secondary">
                  ({selectedClips.length}/{clips.length}개 선택)
                </Text>
              </Space>
            }
            extra={
              clips.length > 0 && (
                <Text type="secondary" className="text-xs">
                  총 {formatDuration(0, totalSelectedDuration)}
                </Text>
              )
            }
          >
            {clips.length === 0 ? (
              <Empty
                description="추출된 구간이 없습니다. AI 구간 추출 버튼을 눌러주세요."
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ) : (
              <div className="max-h-[600px] overflow-y-auto">
                <List
                  dataSource={clips}
                  renderItem={(clip) => (
                    <List.Item key={clip.id} className="!px-0">
                      <div className="flex w-full items-start gap-3">
                        <Checkbox
                          checked={clip.selected}
                          onChange={() => handleToggleSelect(clip.id)}
                          className="mt-1"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <Text strong className="text-sm">
                              {clip.label}
                            </Text>
                            <Tag color="blue" className="text-xs">
                              {formatDuration(clip.start, clip.end)}
                            </Tag>
                          </div>
                          <Text type="secondary" className="text-xs">
                            {formatTime(clip.start)} ~ {formatTime(clip.end)}
                          </Text>
                        </div>
                        <Button
                          type="text"
                          size="small"
                          icon={<PlayCircleOutlined />}
                          onClick={() => handlePreviewClip(clip)}
                          title="미리보기"
                        >
                          미리보기
                        </Button>
                      </div>
                    </List.Item>
                  )}
                />
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Summary Modal */}
      <Modal
        title="선택한 구간 요약"
        open={summaryOpen}
        onCancel={() => setSummaryOpen(false)}
        footer={<Button onClick={() => setSummaryOpen(false)}>닫기</Button>}
      >
        <div className="space-y-3">
          <Text>
            총 <Text strong>{selectedClips.length}개</Text> 구간 선택됨 (
            {formatDuration(0, totalSelectedDuration)})
          </Text>
          <List
            size="small"
            bordered
            dataSource={selectedClips}
            renderItem={(clip, idx) => (
              <List.Item key={clip.id}>
                <Space>
                  <Tag>{idx + 1}</Tag>
                  <Text>{clip.label}</Text>
                  <Text type="secondary">
                    {formatTime(clip.start)} ~ {formatTime(clip.end)}
                  </Text>
                  <Tag color="blue">{formatDuration(clip.start, clip.end)}</Tag>
                </Space>
              </List.Item>
            )}
          />
        </div>
      </Modal>
    </div>
  );
}
