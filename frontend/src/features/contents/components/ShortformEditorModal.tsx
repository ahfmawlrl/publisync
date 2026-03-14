/**
 * ShortformEditorModal — 숏폼 편집 모달.
 *
 * 콘텐츠 작성 화면에서 영상 재생기 + 숏폼 추출 패널을
 * 대형 모달로 제공하여, 작성 흐름을 끊지 않고 숏폼 작업을 완결한다.
 */

import { Empty, Modal, Spin } from 'antd';
import { useRef } from 'react';

import ShortformPanel from '@/features/contents/components/ShortformPanel';
import VideoPlayer, { type VideoPlayerHandle } from '@/shared/components/VideoPlayer';
import useAuthBlobUrl from '@/shared/hooks/useAuthBlobUrl';

interface ShortformEditorModalProps {
  open: boolean;
  onClose: () => void;
  assetId: string | null;
}

export default function ShortformEditorModal({
  open,
  onClose,
  assetId,
}: ShortformEditorModalProps) {
  const videoPlayerRef = useRef<VideoPlayerHandle>(null);
  // 모달이 열려 있을 때만 인증된 blob URL 생성
  const downloadPath = open && assetId ? `/media/${assetId}/download` : null;
  const { blobUrl, loading } = useAuthBlobUrl(downloadPath);

  return (
    <Modal
      title="✂️ 숏폼 편집기"
      open={open}
      onCancel={onClose}
      footer={null}
      width="85vw"
      styles={{ body: { maxHeight: '75vh', overflowY: 'auto' } }}
      destroyOnHidden
    >
      {!assetId ? (
        <Empty
          description="영상을 먼저 업로드하면 숏폼 추출 기능을 사용할 수 있습니다."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          className="py-12"
        />
      ) : loading || !blobUrl ? (
        <div className="flex h-64 items-center justify-center">
          <Spin tip="영상 로딩 중..." />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          {/* Left: Video Player */}
          <div className="lg:col-span-3">
            <div className="overflow-hidden rounded-lg bg-black">
              <VideoPlayer ref={videoPlayerRef} src={blobUrl} />
            </div>
          </div>

          {/* Right: Shortform Panel */}
          <div className="lg:col-span-2">
            <ShortformPanel assetId={assetId} videoPlayerRef={videoPlayerRef} />
          </div>
        </div>
      )}
    </Modal>
  );
}
