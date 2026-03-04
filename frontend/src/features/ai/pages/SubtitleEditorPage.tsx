/**
 * Subtitle Editor Page -- S18 (F03).
 *
 * Two-column layout:
 *   Left (60%): VideoPlayer + WaveformViewer stacked
 *   Right (40%): Subtitle list with editable entries + controls
 *
 * Workflow: Load asset -> Generate subtitles via AI -> Edit -> Export SRT
 */

import { DownloadOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Empty, Input, List, Space, Typography } from 'antd';
import { useCallback, useRef, useState } from 'react';
import { useParams } from 'react-router';

import VideoPlayer from '@/shared/components/VideoPlayer';
import WaveformViewer from '@/shared/components/WaveformViewer';

import AiJobProgress from '../components/AiJobProgress';
import { useCreateSubtitles } from '../hooks/useAiJobs';

const { Title, Text } = Typography;
const { TextArea } = Input;

// ── Types ───────────────────────────────────────────────

interface SubtitleEntry {
  index: number;
  start: string; // "00:00:01,000" SRT format
  end: string;
  text: string;
}

// ── Helpers ─────────────────────────────────────────────

/** Parse "HH:MM:SS,mmm" to total seconds. */
function srtTimeToSeconds(srt: string): number {
  const [hms, ms] = srt.split(',');
  const [h, m, s] = hms.split(':').map(Number);
  return h * 3600 + m * 60 + s + Number(ms) / 1000;
}

/** Convert total seconds to "HH:MM:SS,mmm" SRT format. */
function secondsToSrtTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  const ms = Math.round((totalSeconds - Math.floor(totalSeconds)) * 1000);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

/** Generate an SRT format string from subtitle entries. */
function generateSrt(entries: SubtitleEntry[]): string {
  return entries
    .map((entry) => `${entry.index}\n${entry.start} --> ${entry.end}\n${entry.text}\n`)
    .join('\n');
}

/** Trigger browser download of a text string as a file. */
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

/** Create a blank subtitle entry at a given index. */
function createBlankEntry(index: number): SubtitleEntry {
  return {
    index,
    start: secondsToSrtTime(0),
    end: secondsToSrtTime(1),
    text: '',
  };
}

// ── Component ───────────────────────────────────────────

export default function SubtitleEditorPage() {
  const { assetId } = useParams<{ assetId: string }>();
  const { message } = App.useApp();

  // AI job state
  const [jobId, setJobId] = useState<string | null>(null);
  const createSubtitlesMutation = useCreateSubtitles();

  // Subtitle entries
  const [subtitles, setSubtitles] = useState<SubtitleEntry[]>([]);

  // Ref for tracking whether result was already consumed
  const resultConsumedRef = useRef(false);

  // ── Handlers ────────────────────────────────────────

  const handleGenerateSubtitles = useCallback(() => {
    if (!assetId) return;
    resultConsumedRef.current = false;
    createSubtitlesMutation.mutate(
      { media_asset_id: assetId },
      {
        onSuccess: (data) => {
          setJobId(data.job_id);
          message.info('AI \uc790\ub9c9 \uc0dd\uc131 \uc791\uc5c5\uc744 \uc2dc\uc791\ud588\uc2b5\ub2c8\ub2e4.');
        },
        onError: () => message.error('AI \uc790\ub9c9 \uc0dd\uc131 \uc694\uccad\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.'),
      },
    );
  }, [assetId, createSubtitlesMutation, message]);

  const handleJobComplete = useCallback(
    (result: Record<string, unknown>) => {
      if (resultConsumedRef.current) return;
      resultConsumedRef.current = true;

      // Expect result.subtitles to be an array
      const raw = result.subtitles;
      if (Array.isArray(raw)) {
        const parsed: SubtitleEntry[] = raw.map((item: Record<string, unknown>, idx: number) => ({
          index: idx + 1,
          start: String(item.start ?? '00:00:00,000'),
          end: String(item.end ?? '00:00:01,000'),
          text: String(item.text ?? ''),
        }));
        setSubtitles(parsed);
        message.success(`${parsed.length}\uac1c \uc790\ub9c9\uc774 \uc0dd\uc131\ub418\uc5c8\uc2b5\ub2c8\ub2e4.`);
      } else {
        message.warning('\uc790\ub9c9 \uacb0\uacfc\ub97c \ud30c\uc2f1\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4. \uc218\ub3d9\uc73c\ub85c \uc785\ub825\ud574\uc8fc\uc138\uc694.');
      }
    },
    [message],
  );

  const handleUpdateEntry = useCallback(
    (index: number, field: keyof SubtitleEntry, value: string) => {
      setSubtitles((prev) =>
        prev.map((entry) => (entry.index === index ? { ...entry, [field]: value } : entry)),
      );
    },
    [],
  );

  const handleAddEntry = useCallback(() => {
    setSubtitles((prev) => {
      const newIndex = prev.length > 0 ? Math.max(...prev.map((e) => e.index)) + 1 : 1;
      const lastEntry = prev[prev.length - 1];
      const newEntry: SubtitleEntry = lastEntry
        ? {
            index: newIndex,
            start: lastEntry.end,
            end: secondsToSrtTime(srtTimeToSeconds(lastEntry.end) + 2),
            text: '',
          }
        : createBlankEntry(newIndex);
      return [...prev, newEntry];
    });
  }, []);

  const handleRemoveEntry = useCallback((index: number) => {
    setSubtitles((prev) => {
      const filtered = prev.filter((e) => e.index !== index);
      // Re-index
      return filtered.map((entry, idx) => ({ ...entry, index: idx + 1 }));
    });
  }, []);

  const handleExportSrt = useCallback(() => {
    if (subtitles.length === 0) {
      message.warning('\ub0b4\ubcf4\ub0bc \uc790\ub9c9\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.');
      return;
    }
    const srtContent = generateSrt(subtitles);
    downloadAsFile(srtContent, `subtitles_${assetId ?? 'unknown'}.srt`);
    message.success('SRT \ud30c\uc77c\uc744 \ub2e4\uc6b4\ub85c\ub4dc\ud588\uc2b5\ub2c8\ub2e4.');
  }, [subtitles, assetId, message]);

  const handleCloseJobProgress = useCallback(() => {
    setJobId(null);
  }, []);

  // ── Render ──────────────────────────────────────────

  if (!assetId) {
    return (
      <div className="p-6">
        <Title level={4}>\ubbf8\ub514\uc5b4 \uc790\uc0b0 ID\uac00 \ud544\uc694\ud569\ub2c8\ub2e4</Title>
      </div>
    );
  }

  const isJobRunning = !!jobId;
  const isGenerating = createSubtitlesMutation.isPending;

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          자막 편집기
        </Title>
        <Space>
          <Button
            type="primary"
            onClick={handleGenerateSubtitles}
            loading={isGenerating}
            disabled={isJobRunning}
          >
            AI 자막 생성
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExportSrt}
            disabled={subtitles.length === 0}
          >
            SRT 내보내기
          </Button>
        </Space>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        {/* Left column: Video + Waveform (60%) */}
        <div className="space-y-4 lg:col-span-3">
          <Card size="small" title="미리보기">
            <VideoPlayer src={`/api/v1/media/${assetId}/download`} />
          </Card>
          <Card size="small" title="파형">
            <WaveformViewer audioUrl={`/api/v1/media/${assetId}/download`} />
          </Card>
        </div>

        {/* Right column: Subtitle list + controls (40%) */}
        <div className="space-y-4 lg:col-span-2">
          {/* AI Job Progress */}
          {isJobRunning && (
            <AiJobProgress
              jobId={jobId}
              title="AI 자막 생성"
              onComplete={handleJobComplete}
              onClose={handleCloseJobProgress}
            />
          )}

          {/* Subtitle entries */}
          <Card
            size="small"
            title={
              <Space>
                <span>자막 목록</span>
                <Text type="secondary">({subtitles.length}개)</Text>
              </Space>
            }
            extra={
              <Button
                type="text"
                icon={<PlusOutlined />}
                onClick={handleAddEntry}
                size="small"
              >
                추가
              </Button>
            }
          >
            {subtitles.length === 0 ? (
              <Empty
                description="자막이 없습니다. AI 생성 버튼을 누르거나 수동으로 추가하세요."
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ) : (
              <div className="max-h-[600px] overflow-y-auto">
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
        </div>
      </div>
    </div>
  );
}
