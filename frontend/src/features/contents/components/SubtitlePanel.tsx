/**
 * SubtitlePanel — 자막 편집 인라인 패널.
 *
 * ContentEditorPage 도구 바에서 [자막] 선택 시 표시.
 * 기존 SubtitleEditorPage의 자막 목록/편집 로직을 props 기반으로 리팩터링.
 * VideoPlayer는 상단 MediaMainArea와 공유 (별도 인스턴스 X).
 */

import { DownloadOutlined, PlusOutlined, SaveOutlined, VideoCameraOutlined } from '@ant-design/icons';
import { App, Button, Card, Empty, Input, List, Space, Typography } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';

import AiJobProgress from '@/features/ai/components/AiJobProgress';
import { useCreateSubtitles, useSaveSubtitles, useSubtitleBurnin } from '@/features/ai/hooks/useAiJobs';
import { useMediaAsset } from '@/features/media/hooks/useMedia';

const { Text } = Typography;
const { TextArea } = Input;

interface SubtitleEntry {
  index: number;
  start: string;
  end: string;
  text: string;
}

function secondsToSrtTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  const ms = Math.round((totalSeconds - Math.floor(totalSeconds)) * 1000);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

function srtTimeToSeconds(srt: string): number {
  const [hms, ms] = srt.split(',');
  const [h, m, s] = hms.split(':').map(Number);
  return h * 3600 + m * 60 + s + Number(ms) / 1000;
}

function generateSrt(entries: SubtitleEntry[]): string {
  return entries
    .map((entry) => `${entry.index}\n${entry.start} --> ${entry.end}\n${entry.text}\n`)
    .join('\n');
}

function downloadAsFile(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

interface SubtitlePanelProps {
  assetId: string | null;
}

export default function SubtitlePanel({ assetId }: SubtitlePanelProps) {
  const { message } = App.useApp();

  const [jobId, setJobId] = useState<string | null>(null);
  const [burninJobId, setBurninJobId] = useState<string | null>(null);
  const createSubtitlesMutation = useCreateSubtitles();
  const saveSubtitlesMutation = useSaveSubtitles();
  const burninMutation = useSubtitleBurnin();
  const [subtitles, setSubtitles] = useState<SubtitleEntry[]>([]);
  const resultConsumedRef = useRef(false);
  const initialLoadDoneRef = useRef(false);

  // assetId 변경 시 초기화
  useEffect(() => {
    initialLoadDoneRef.current = false;
    setSubtitles([]);
  }, [assetId]);

  // 기존 자막 자동 로드
  const { data: mediaAsset } = useMediaAsset(assetId);

  useEffect(() => {
    if (initialLoadDoneRef.current) return;
    if (!mediaAsset) return;

    const meta = mediaAsset.metadata as Record<string, unknown> | null;
    const segments = meta?.subtitles as
      | { segments?: Array<{ start: number; end: number; text: string }> }
      | undefined;

    if (segments?.segments && segments.segments.length > 0) {
      const loaded: SubtitleEntry[] = segments.segments.map((seg, idx) => ({
        index: idx + 1,
        start: secondsToSrtTime(seg.start),
        end: secondsToSrtTime(seg.end),
        text: seg.text,
      }));
      setSubtitles(loaded);
      initialLoadDoneRef.current = true;
      message.info(`저장된 자막 ${loaded.length}개를 불러왔습니다.`);
    }
  }, [mediaAsset, message]);

  const handleGenerateSubtitles = useCallback(() => {
    if (!assetId) {
      message.warning('먼저 영상을 업로드하세요.');
      return;
    }
    resultConsumedRef.current = false;
    createSubtitlesMutation.mutate(
      { media_asset_id: assetId },
      {
        onSuccess: (data) => {
          setJobId(data.job_id);
          message.info('AI 자막 생성 작업을 시작했습니다.');
        },
        onError: () => message.error('AI 자막 생성 요청에 실패했습니다.'),
      },
    );
  }, [assetId, createSubtitlesMutation, message]);

  const handleJobComplete = useCallback(
    (result: Record<string, unknown>) => {
      if (resultConsumedRef.current) return;
      resultConsumedRef.current = true;

      const raw = result.subtitles;
      if (Array.isArray(raw)) {
        const parsed: SubtitleEntry[] = raw.map(
          (item: Record<string, unknown>, idx: number) => ({
            index: idx + 1,
            start: String(item.start ?? '00:00:00,000'),
            end: String(item.end ?? '00:00:01,000'),
            text: String(item.text ?? ''),
          }),
        );
        setSubtitles(parsed);
        message.success(`${parsed.length}개 자막이 생성되었습니다.`);
      } else {
        message.warning('자막 결과를 파싱할 수 없습니다. 수동으로 입력해주세요.');
      }
    },
    [message],
  );

  const handleUpdateEntry = useCallback(
    (index: number, field: keyof SubtitleEntry, value: string) => {
      setSubtitles((prev) =>
        prev.map((entry) =>
          entry.index === index ? { ...entry, [field]: value } : entry,
        ),
      );
    },
    [],
  );

  const handleAddEntry = useCallback(() => {
    setSubtitles((prev) => {
      const newIndex =
        prev.length > 0 ? Math.max(...prev.map((e) => e.index)) + 1 : 1;
      const lastEntry = prev[prev.length - 1];
      const newEntry: SubtitleEntry = lastEntry
        ? {
            index: newIndex,
            start: lastEntry.end,
            end: secondsToSrtTime(srtTimeToSeconds(lastEntry.end) + 2),
            text: '',
          }
        : { index: newIndex, start: secondsToSrtTime(0), end: secondsToSrtTime(1), text: '' };
      return [...prev, newEntry];
    });
  }, []);

  const handleRemoveEntry = useCallback((index: number) => {
    setSubtitles((prev) => {
      const filtered = prev.filter((e) => e.index !== index);
      return filtered.map((entry, idx) => ({ ...entry, index: idx + 1 }));
    });
  }, []);

  const handleExportSrt = useCallback(() => {
    if (subtitles.length === 0) {
      message.warning('내보낼 자막이 없습니다.');
      return;
    }
    const srtContent = generateSrt(subtitles);
    downloadAsFile(srtContent, `subtitles_${assetId ?? 'unknown'}.srt`);
    message.success('SRT 파일을 다운로드했습니다.');
  }, [subtitles, assetId, message]);

  const handleSaveToServer = useCallback(async () => {
    if (!assetId || subtitles.length === 0) {
      message.warning('저장할 자막이 없습니다.');
      return;
    }
    try {
      await saveSubtitlesMutation.mutateAsync({
        mediaAssetId: assetId,
        subtitles: subtitles.map((s) => ({
          start: srtTimeToSeconds(s.start),
          end: srtTimeToSeconds(s.end),
          text: s.text,
        })),
      });
      message.success('자막이 서버에 저장되었습니다.');
    } catch {
      message.error('자막 저장에 실패했습니다.');
    }
  }, [assetId, subtitles, saveSubtitlesMutation, message]);

  const handleBurnin = useCallback(async () => {
    if (!assetId) {
      message.warning('먼저 영상을 업로드하세요.');
      return;
    }
    if (subtitles.length === 0) {
      message.warning('합성할 자막이 없습니다. 먼저 자막을 생성하거나 추가하세요.');
      return;
    }
    // 자막을 먼저 서버에 저장한 후 합성 요청
    try {
      await saveSubtitlesMutation.mutateAsync({
        mediaAssetId: assetId,
        subtitles: subtitles.map((s) => ({
          start: srtTimeToSeconds(s.start),
          end: srtTimeToSeconds(s.end),
          text: s.text,
        })),
      });
    } catch {
      message.error('자막 저장에 실패하여 합성을 진행할 수 없습니다.');
      return;
    }
    burninMutation.mutate(
      { media_asset_id: assetId },
      {
        onSuccess: (data) => {
          setBurninJobId(data.job_id);
          message.info('자막 합성 영상 생성을 시작했습니다.');
        },
        onError: () => message.error('자막 합성 요청에 실패했습니다.'),
      },
    );
  }, [assetId, subtitles, saveSubtitlesMutation, burninMutation, message]);

  const handleBurninComplete = useCallback(
    (result: Record<string, unknown>) => {
      const outputAssetId = result.output_asset_id as string | undefined;
      if (outputAssetId) {
        message.success('자막이 합성된 영상이 생성되었습니다. 미디어 라이브러리에서 확인하세요.');
      } else {
        message.success('자막 합성이 완료되었습니다.');
      }
    },
    [message],
  );

  if (!assetId) {
    return (
      <Card size="small">
        <Empty
          description="영상을 업로드하면 자막 편집 기능을 사용할 수 있습니다."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  const isJobRunning = !!jobId || !!burninJobId;

  return (
    <Card size="small">
      {/* Controls */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Button
          type="primary"
          size="small"
          onClick={handleGenerateSubtitles}
          loading={createSubtitlesMutation.isPending}
          disabled={isJobRunning}
        >
          AI 자막 생성
        </Button>
        <Button
          size="small"
          icon={<SaveOutlined />}
          onClick={handleSaveToServer}
          loading={saveSubtitlesMutation.isPending}
          disabled={subtitles.length === 0}
        >
          서버에 저장
        </Button>
        <Button
          size="small"
          icon={<VideoCameraOutlined />}
          onClick={handleBurnin}
          loading={burninMutation.isPending}
          disabled={subtitles.length === 0 || isJobRunning}
        >
          자막 합성 영상
        </Button>
        <Button
          size="small"
          icon={<DownloadOutlined />}
          onClick={handleExportSrt}
          disabled={subtitles.length === 0}
        >
          SRT 내보내기
        </Button>
        <Button
          size="small"
          icon={<PlusOutlined />}
          onClick={handleAddEntry}
        >
          추가
        </Button>
      </div>

      {/* Job Progress — Subtitle Generation */}
      {jobId && (
        <div className="mb-3">
          <AiJobProgress
            jobId={jobId}
            title="AI 자막 생성"
            onComplete={handleJobComplete}
            onClose={() => setJobId(null)}
          />
        </div>
      )}

      {/* Job Progress — Subtitle Burn-in */}
      {burninJobId && (
        <div className="mb-3">
          <AiJobProgress
            jobId={burninJobId}
            title="자막 합성 영상 생성"
            onComplete={handleBurninComplete}
            onClose={() => setBurninJobId(null)}
          />
        </div>
      )}

      {/* Subtitle List */}
      {subtitles.length === 0 ? (
        <Empty
          description="자막이 없습니다. AI 생성 버튼을 누르거나 수동으로 추가하세요."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <div className="max-h-[400px] overflow-y-auto">
          <List
            dataSource={subtitles}
            renderItem={(entry) => (
              <List.Item key={entry.index} className="!px-0">
                <div className="w-full space-y-2">
                  <div className="flex items-center justify-between">
                    <Text strong className="text-xs">
                      #{entry.index}
                    </Text>
                    <Button
                      type="text"
                      danger
                      size="small"
                      onClick={() => handleRemoveEntry(entry.index)}
                    >
                      삭제
                    </Button>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      size="small"
                      value={entry.start}
                      onChange={(e) =>
                        handleUpdateEntry(entry.index, 'start', e.target.value)
                      }
                      placeholder="00:00:00,000"
                      className="w-36"
                    />
                    <Text type="secondary">~</Text>
                    <Input
                      size="small"
                      value={entry.end}
                      onChange={(e) =>
                        handleUpdateEntry(entry.index, 'end', e.target.value)
                      }
                      placeholder="00:00:00,000"
                      className="w-36"
                    />
                  </div>
                  <TextArea
                    size="small"
                    value={entry.text}
                    onChange={(e) =>
                      handleUpdateEntry(entry.index, 'text', e.target.value)
                    }
                    placeholder="자막 텍스트를 입력하세요"
                    autoSize={{ minRows: 1, maxRows: 3 }}
                  />
                </div>
              </List.Item>
            )}
          />
        </div>
      )}
    </Card>
  );
}
