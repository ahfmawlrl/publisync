/**
 * ShortformPanel — 숏폼 추출 인라인 패널.
 *
 * ContentEditorPage 도구 바에서 [숏폼 추출] 선택 시 표시.
 * 기존 ShortformEditorPage의 구간 추출 로직을 props 기반으로 리팩터링.
 * VideoPlayer는 상단 MediaMainArea와 공유.
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

import AiJobProgress from '@/features/ai/components/AiJobProgress';
import { useConfirmShortform, useCreateShortform } from '@/features/ai/hooks/useAiJobs';
import type { VideoPlayerHandle } from '@/shared/components/VideoPlayer';

const { Text } = Typography;

interface ClipSegment {
  id: string;
  start: number;
  end: number;
  label: string;
  selected: boolean;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatDuration(start: number, end: number): string {
  const duration = Math.max(0, end - start);
  if (duration < 60) return `${duration.toFixed(1)}초`;
  return `${Math.floor(duration / 60)}분 ${Math.floor(duration % 60)}초`;
}

interface ShortformPanelProps {
  assetId: string | null;
  videoPlayerRef?: React.RefObject<VideoPlayerHandle | null>;
}

export default function ShortformPanel({ assetId, videoPlayerRef }: ShortformPanelProps) {
  const { message } = App.useApp();

  const [jobId, setJobId] = useState<string | null>(null);
  const createShortformMutation = useCreateShortform();
  const confirmShortformMutation = useConfirmShortform();
  const [clips, setClips] = useState<ClipSegment[]>([]);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const resultConsumedRef = useRef(false);

  const handleExtractShortform = useCallback(() => {
    if (!assetId) {
      message.warning('먼저 영상을 업로드하세요.');
      return;
    }
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
        message.warning('구간 결과를 파싱할 수 없습니다.');
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
      if (videoPlayerRef?.current?.seekTo) {
        videoPlayerRef.current.seekTo(clip.start);
        message.info(`${formatTime(clip.start)}부터 재생합니다.`);
      }
    },
    [videoPlayerRef, message],
  );

  const handleShowSummary = useCallback(() => {
    const selected = clips.filter((c) => c.selected);
    if (selected.length === 0) {
      message.warning('선택된 구간이 없습니다.');
      return;
    }
    setSummaryOpen(true);
  }, [clips, message]);

  const handleConfirm = useCallback(async () => {
    const selected = clips.filter((c) => c.selected);
    if (!assetId || selected.length === 0) return;
    try {
      await confirmShortformMutation.mutateAsync({
        media_asset_id: assetId,
        clips: selected.map((c) => ({
          id: c.id,
          start: c.start,
          end: c.end,
          label: c.label,
        })),
      });
      message.success('숏폼 구간이 확정되었습니다.');
      setSummaryOpen(false);
    } catch {
      message.error('숏폼 확정에 실패했습니다.');
    }
  }, [assetId, clips, confirmShortformMutation, message]);

  const selectedClips = clips.filter((c) => c.selected);
  const totalSelectedDuration = selectedClips.reduce(
    (acc, clip) => acc + Math.max(0, clip.end - clip.start),
    0,
  );

  if (!assetId) {
    return (
      <Card size="small">
        <Empty
          description="영상을 업로드하면 숏폼 추출 기능을 사용할 수 있습니다."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  const isJobRunning = !!jobId;

  return (
    <Card size="small">
      {/* Controls */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Button
          type="primary"
          size="small"
          onClick={handleExtractShortform}
          loading={createShortformMutation.isPending}
          disabled={isJobRunning}
        >
          AI 구간 추출
        </Button>
        <Button
          size="small"
          icon={<CheckOutlined />}
          onClick={handleShowSummary}
          disabled={selectedClips.length === 0}
        >
          선택한 구간 확인 ({selectedClips.length}개)
        </Button>
        {clips.length > 0 && (
          <Text type="secondary" className="text-xs">
            총 {formatDuration(0, totalSelectedDuration)}
          </Text>
        )}
      </div>

      {/* Job Progress */}
      {isJobRunning && (
        <div className="mb-3">
          <AiJobProgress
            jobId={jobId}
            title="AI 구간 추출"
            onComplete={handleJobComplete}
            onClose={() => setJobId(null)}
          />
        </div>
      )}

      {/* Clip List */}
      {clips.length === 0 ? (
        <Empty
          description="추출된 구간이 없습니다. AI 구간 추출 버튼을 눌러주세요."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <div className="max-h-[400px] overflow-y-auto">
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
                  >
                    미리보기
                  </Button>
                </div>
              </List.Item>
            )}
          />
        </div>
      )}

      {/* Summary Modal */}
      <Modal
        title="선택한 구간 요약"
        open={summaryOpen}
        onCancel={() => setSummaryOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setSummaryOpen(false)}>닫기</Button>
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={handleConfirm}
              loading={confirmShortformMutation.isPending}
            >
              확정
            </Button>
          </Space>
        }
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
    </Card>
  );
}
