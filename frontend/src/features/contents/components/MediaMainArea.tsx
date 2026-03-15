/**
 * MediaMainArea — 미디어 메인 영역.
 *
 * 콘텐츠 에디터 상단 메인 영역.
 * - 초기: 업로드 드롭존 (드래그 앤 드롭 + 미디어 라이브러리)
 * - 영상 업로드 완료 → VideoPlayer + WaveformViewer 자동 전환
 * - 이미지 업로드 완료 → 이미지 갤러리 뷰 전환
 * - 편집 모드: 기존 미디어가 있으면 즉시 플레이어/갤러리 표시
 */

import {
  DeleteOutlined,
  FolderOpenOutlined,
  InboxOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { App, Button, Image, Space, Typography } from 'antd';
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useDropzone } from 'react-dropzone';

import MediaLibraryPickerModal from '@/features/contents/components/MediaLibraryPickerModal';
import apiClient from '@/shared/api/client';
import VideoPlayer, { type VideoPlayerHandle } from '@/shared/components/VideoPlayer';
import WaveformViewer from '@/shared/components/WaveformViewer';

const { Text } = Typography;

const ACCEPTED_TYPES: Record<string, string[]> = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/gif': ['.gif'],
  'image/webp': ['.webp'],
  'video/mp4': ['.mp4'],
  'video/webm': ['.webm'],
  'audio/mpeg': ['.mp3'],
  'audio/wav': ['.wav'],
};

const MAX_SIZE = 100 * 1024 * 1024;

const VIDEO_EXTS = /\.(mp4|webm|mov|avi|mkv)$/i;
const IMAGE_EXTS = /\.(jpg|jpeg|png|gif|webp)$/i;

type MediaMode = 'empty' | 'video' | 'image';

export interface MediaMainAreaHandle {
  getVideoPlayerRef: () => VideoPlayerHandle | null;
}

interface MediaMainAreaProps {
  value?: string[];
  onChange?: (urls: string[]) => void;
  maxFiles?: number;
  onTimeUpdate?: (currentTime: number) => void;
  onAssetIdChange?: (assetId: string | null) => void;
}

const MediaMainArea = forwardRef<MediaMainAreaHandle, MediaMainAreaProps>(
  function MediaMainArea({ value = [], onChange, maxFiles = 10, onTimeUpdate, onAssetIdChange }, ref) {
    const { message } = App.useApp();
    const videoPlayerRef = useRef<VideoPlayerHandle>(null);
    const [pickerOpen, setPickerOpen] = useState(false);
    const [uploading, setUploading] = useState(false);

    useImperativeHandle(ref, () => ({
      getVideoPlayerRef: () => videoPlayerRef.current,
    }));

    /** Detect media mode from current URLs. */
    const mediaMode: MediaMode = useMemo(() => {
      if (!value.length) return 'empty';
      if (value.some((url) => VIDEO_EXTS.test(url))) return 'video';
      if (value.some((url) => IMAGE_EXTS.test(url))) return 'image';
      return 'empty';
    }, [value]);

    const videoUrl = useMemo(
      () => value.find((url) => VIDEO_EXTS.test(url)) ?? null,
      [value],
    );

    const imageUrls = useMemo(
      () => value.filter((url) => IMAGE_EXTS.test(url)),
      [value],
    );

    // 기존 비디오 URL에서 assetId 자동 해석 (편집 모드)
    const assetIdResolvedRef = useRef(false);
    useEffect(() => {
      if (assetIdResolvedRef.current || !onAssetIdChange || !videoUrl) return;
      // /api/v1/storage/files/{object_key} → object_key에서 filename 추출
      const parts = videoUrl.split('/');
      const filename = parts[parts.length - 1];
      if (!filename || !VIDEO_EXTS.test(filename)) return;
      assetIdResolvedRef.current = true;
      apiClient
        .get<{ success: boolean; data: { id: string; media_type: string }[] }>('/media', {
          params: { search: filename, limit: 1 },
        })
        .then((res) => {
          const items = Array.isArray(res.data.data) ? res.data.data : [];
          const video = items.find((a) => a.media_type === 'VIDEO');
          if (video) onAssetIdChange(video.id);
        })
        .catch(() => {});
    }, [videoUrl, onAssetIdChange]);

    const reportChange = useCallback(
      (urls: string[]) => {
        onChange?.(urls);
      },
      [onChange],
    );

    /** Upload a single file via presigned URL + register to media_assets. */
    const uploadFile = useCallback(
      async (file: File): Promise<string> => {
        try {
          // Step 1: Get presigned upload URL
          const presignedRes = await apiClient.post<{
            success: boolean;
            data: { upload_url: string; object_key: string; public_url: string };
          }>('/media/presigned-upload', {
            filename: file.name,
            content_type: file.type,
            file_size: file.size,
          });

          if (!presignedRes.data.success) throw new Error('Presigned URL 발급 실패');

          const { upload_url, object_key, public_url } = presignedRes.data.data;

          // Step 2: Upload file to storage
          await new Promise<void>((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('PUT', upload_url, true);
            xhr.setRequestHeader('Content-Type', file.type);
            xhr.onload = () =>
              xhr.status >= 200 && xhr.status < 300
                ? resolve()
                : reject(new Error(`Upload failed: ${xhr.status}`));
            xhr.onerror = () => reject(new Error('Network error'));
            xhr.send(file);
          });

          // Step 3: Register to media_assets for media library
          try {
            const assetRes = await apiClient.post<{
              success: boolean;
              data: { id: string };
            }>('/media/upload', {
              filename: object_key.split('/').pop() || file.name,
              original_filename: file.name,
              content_type: file.type,
              object_key,
              file_size: file.size,
            });
            // 비디오 파일이면 assetId를 부모에게 전달
            if (file.type.startsWith('video/') && assetRes.data?.data?.id) {
              onAssetIdChange?.(assetRes.data.data.id);
            }
          } catch {
            // asset 등록 실패해도 파일 자체는 업로드 완료 — 콘텐츠 작성은 진행
            console.warn(`media_assets 등록 실패: ${file.name}`);
          }

          return public_url;
        } catch {
          const blobUrl = URL.createObjectURL(file);
          message.warning(
            `${file.name}: 스토리지 미연결 — 로컬 미리보기로 대체됩니다.`,
          );
          return blobUrl;
        }
      },
      [message, onAssetIdChange],
    );

    const onDrop = useCallback(
      async (acceptedFiles: File[]) => {
        const remaining = maxFiles - value.length;
        if (remaining <= 0) {
          message.warning(`최대 ${maxFiles}개 파일까지 업로드 가능합니다`);
          return;
        }
        const filesToUpload = acceptedFiles.slice(0, remaining);
        setUploading(true);
        try {
          const urls = await Promise.all(filesToUpload.map(uploadFile));
          reportChange([...value, ...urls]);
        } finally {
          setUploading(false);
        }
      },
      [maxFiles, value, message, uploadFile, reportChange],
    );

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
      onDrop,
      accept: ACCEPTED_TYPES,
      maxSize: MAX_SIZE,
      noClick: mediaMode !== 'empty',
      noDrag: mediaMode !== 'empty',
    });

    const handlePickerSelect = useCallback(
      (items: { url: string; filename: string; size: number; assetId?: string; mediaType?: string }[]) => {
        const remaining = maxFiles - value.length;
        const toAdd = items.slice(0, remaining);
        if (toAdd.length === 0) return;
        reportChange([...value, ...toAdd.map((i) => i.url)]);
        // 비디오 asset 선택 시 assetId 전달
        const videoItem = toAdd.find((i) => i.mediaType === 'VIDEO');
        if (videoItem?.assetId) {
          onAssetIdChange?.(videoItem.assetId);
        }
      },
      [maxFiles, value, reportChange, onAssetIdChange],
    );

    const handleRemoveFile = useCallback(
      (index: number) => {
        const removedUrl = value[index];
        const newUrls = value.filter((_, i) => i !== index);
        reportChange(newUrls);
        // 비디오 파일이 삭제되면 assetId 초기화
        if (removedUrl && VIDEO_EXTS.test(removedUrl)) {
          onAssetIdChange?.(null);
        }
      },
      [value, reportChange, onAssetIdChange],
    );

    // ── Render: Empty / Upload Dropzone ──
    if (mediaMode === 'empty') {
      return (
        <div className="space-y-3">
          <div
            {...getRootProps()}
            className={`cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
              isDragActive
                ? 'border-blue-400 bg-blue-50'
                : 'border-gray-300 hover:border-blue-300'
            }`}
          >
            <input {...getInputProps()} />
            <InboxOutlined className="mb-3 text-5xl text-gray-400" />
            <p className="text-base text-gray-600">
              {isDragActive
                ? '파일을 여기에 놓으세요'
                : '클릭하거나 파일을 드래그하여 업로드'}
            </p>
            <Text type="secondary" className="text-sm">
              동영상, 이미지 · 최대 100MB · 최대 {maxFiles}개
            </Text>
            {uploading && (
              <p className="mt-2 text-sm text-blue-500">업로드 중...</p>
            )}
          </div>
          <Button
            icon={<FolderOpenOutlined />}
            onClick={() => setPickerOpen(true)}
            block
          >
            미디어 라이브러리에서 선택
          </Button>
          <MediaLibraryPickerModal
            open={pickerOpen}
            onClose={() => setPickerOpen(false)}
            onSelect={handlePickerSelect}
            maxSelect={maxFiles}
          />
        </div>
      );
    }

    // ── Render: Video Mode ──
    if (mediaMode === 'video' && videoUrl) {
      return (
        <div className="space-y-2">
          <div className="overflow-hidden rounded-lg bg-black">
            <VideoPlayer
              ref={videoPlayerRef}
              src={videoUrl}
              onTimeUpdate={onTimeUpdate}
            />
          </div>
          <WaveformViewer
            audioUrl={videoUrl}
            height={60}
            className="rounded-lg"
          />
          <div className="flex items-center justify-between">
            <Text type="secondary" className="text-xs">
              {value.length}개 미디어 첨부됨
            </Text>
            <Space size={4}>
              <Button
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setPickerOpen(true)}
                disabled={value.length >= maxFiles}
              >
                파일 추가
              </Button>
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => {
                  const videoIndex = value.findIndex((url) => VIDEO_EXTS.test(url));
                  if (videoIndex >= 0) handleRemoveFile(videoIndex);
                }}
              >
                삭제
              </Button>
            </Space>
          </div>
          <MediaLibraryPickerModal
            open={pickerOpen}
            onClose={() => setPickerOpen(false)}
            onSelect={handlePickerSelect}
            maxSelect={maxFiles - value.length}
          />
        </div>
      );
    }

    // ── Render: Image Mode ──
    return (
      <div className="space-y-2">
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <Image.PreviewGroup>
            <div className="flex flex-wrap gap-3">
              {imageUrls.map((url, idx) => {
                const globalIdx = value.indexOf(url);
                return (
                  <div key={url} className="group relative">
                    <Image
                      src={url}
                      width={160}
                      height={120}
                      className="rounded-lg object-cover"
                      fallback="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>"
                      alt={`이미지 ${idx + 1}`}
                    />
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      className="absolute right-1 top-1 opacity-0 group-hover:opacity-100"
                      onClick={() => handleRemoveFile(globalIdx)}
                    />
                  </div>
                );
              })}
            </div>
          </Image.PreviewGroup>
        </div>
        <div className="flex items-center justify-between">
          <Text type="secondary" className="text-xs">
            {imageUrls.length}개 이미지
          </Text>
          <Space size={4}>
            <Button
              size="small"
              icon={<PlusOutlined />}
              onClick={() => setPickerOpen(true)}
              disabled={value.length >= maxFiles}
            >
              파일 추가
            </Button>
          </Space>
        </div>
        <MediaLibraryPickerModal
          open={pickerOpen}
          onClose={() => setPickerOpen(false)}
          onSelect={handlePickerSelect}
          maxSelect={maxFiles - value.length}
        />
      </div>
    );
  },
);

export default MediaMainArea;
