/**
 * SubtitleEditorModal — 자막 편집 모달.
 *
 * 콘텐츠 작성 화면에서 영상 재생기 + 파형 뷰어 + 자막 편집 패널을
 * 대형 모달로 제공하여, 작성 흐름을 끊지 않고 자막 작업을 완결한다.
 */

import { Empty, Modal, Spin } from 'antd';

import SubtitlePanel from '@/features/contents/components/SubtitlePanel';
import VideoPlayer from '@/shared/components/VideoPlayer';
import WaveformViewer from '@/shared/components/WaveformViewer';
import useAuthBlobUrl from '@/shared/hooks/useAuthBlobUrl';

interface SubtitleEditorModalProps {
  open: boolean;
  onClose: () => void;
  assetId: string | null;
}

export default function SubtitleEditorModal({
  open,
  onClose,
  assetId,
}: SubtitleEditorModalProps) {
  // 모달이 열려 있을 때만 인증된 blob URL 생성
  const downloadPath = open && assetId ? `/media/${assetId}/download` : null;
  const { blobUrl, loading } = useAuthBlobUrl(downloadPath);

  return (
    <Modal
      title="🎬 자막 편집기"
      open={open}
      onCancel={onClose}
      footer={null}
      width="85vw"
      styles={{ body: { maxHeight: '75vh', overflowY: 'auto' } }}
      destroyOnHidden
    >
      {!assetId ? (
        <Empty
          description="영상을 먼저 업로드하면 자막 편집 기능을 사용할 수 있습니다."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          className="py-12"
        />
      ) : loading || !blobUrl ? (
        <div className="flex h-64 items-center justify-center">
          <Spin tip="영상 로딩 중..." />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          {/* Left: Video + Waveform */}
          <div className="space-y-4 lg:col-span-3">
            <div className="overflow-hidden rounded-lg bg-black">
              <VideoPlayer src={blobUrl} />
            </div>
            <div className="rounded-lg border border-gray-200 p-2">
              <WaveformViewer audioUrl={blobUrl} height={70} />
            </div>
          </div>

          {/* Right: Subtitle Panel */}
          <div className="lg:col-span-2">
            <SubtitlePanel assetId={assetId} />
          </div>
        </div>
      )}
    </Modal>
  );
}
