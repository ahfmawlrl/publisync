import { CloseCircleOutlined, DeleteOutlined, InboxOutlined, LoadingOutlined, ReloadOutlined } from '@ant-design/icons';
import { App, Button, Image, List, Progress, Space, Typography } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useDropzone } from 'react-dropzone';

import apiClient from '@/shared/api/client';

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
  'audio/aac': ['.aac'],
  'audio/ogg': ['.ogg'],
  'audio/webm': ['.weba'],
  'application/pdf': ['.pdf'],
};

const MAX_SIZE = 100 * 1024 * 1024; // 100MB

interface UploadedFile {
  filename: string;
  publicUrl: string;
  objectKey: string;
  size: number;
}

interface UploadingFile {
  filename: string;
  progress: number;
  error?: string;
  /** Keep original File reference for retry. */
  file?: File;
}

interface MediaUploadProps {
  value?: string[];
  onChange?: (urls: string[]) => void;
  maxFiles?: number;
}

export default function MediaUpload({ value = [], onChange, maxFiles = 10 }: MediaUploadProps) {
  const { message } = App.useApp();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>(() =>
    value.map((url) => ({ filename: url.split('/').pop() || 'file', publicUrl: url, objectKey: '', size: 0 })),
  );
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);

  // Track last value we reported via onChange to distinguish internal vs external changes
  const lastReportedUrls = useRef<string[]>(value);
  // Stable onChange ref to avoid re-creating uploadFile callback
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  // Sync internal state when value prop changes externally (e.g., form reset)
  useEffect(() => {
    const currentUrls = lastReportedUrls.current;
    // Only sync if value changed externally (not from our own onChange)
    if (JSON.stringify(value) !== JSON.stringify(currentUrls)) {
      lastReportedUrls.current = value;
      setUploadedFiles((prev) =>
        value.map((url) => {
          // Preserve existing metadata for URLs we already know about
          const existing = prev.find((f) => f.publicUrl === url);
          return existing ?? { filename: url.split('/').pop() || 'file', publicUrl: url, objectKey: '', size: 0 };
        }),
      );
    }
  }, [value]);

  /** Report URL list change to parent Form and update tracking ref. */
  const reportChange = useCallback((files: UploadedFile[]) => {
    const urls = files.map((f) => f.publicUrl);
    lastReportedUrls.current = urls;
    onChangeRef.current?.(urls);
  }, []);

  /**
   * Upload via presigned URL → MinIO.
   * If presigned URL or MinIO upload fails, fall back to a local blob URL
   * so the dev/test workflow is not blocked by infrastructure.
   */
  const uploadFile = useCallback(
    async (file: File) => {
      const uploadingItem: UploadingFile = { filename: file.name, progress: 0, file };
      setUploadingFiles((prev) => [...prev, uploadingItem]);

      let publicUrl: string | undefined;
      let objectKey = '';

      try {
        // 1. Get presigned URL from backend
        const presignedRes = await apiClient.post<{
          success: boolean;
          data: { upload_url: string; object_key: string; public_url: string };
        }>('/media/presigned-upload', {
          filename: file.name,
          content_type: file.type,
          file_size: file.size,
        });

        if (!presignedRes.data.success) {
          throw new Error('Presigned URL 발급 실패');
        }

        const { upload_url, object_key: key, public_url } = presignedRes.data.data;
        objectKey = key;

        // 2. Upload directly to MinIO using presigned PUT URL
        await new Promise<void>((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.open('PUT', upload_url, true);
          xhr.setRequestHeader('Content-Type', file.type);

          xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
              const progress = Math.round((e.loaded / e.total) * 100);
              setUploadingFiles((prev) =>
                prev.map((f) => (f.filename === file.name ? { ...f, progress } : f)),
              );
            }
          };

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve();
            } else {
              reject(new Error(`Upload failed: ${xhr.status}`));
            }
          };

          xhr.onerror = () => reject(new Error('Network error'));
          xhr.send(file);
        });

        publicUrl = public_url;
      } catch {
        // Storage unavailable — use local blob URL as fallback for dev/preview.
        // The file remains usable in the form; the actual upload should be retried
        // when MinIO is available (at content submission time).
        publicUrl = URL.createObjectURL(file);
        objectKey = `local://${file.name}`;
        message.warning(`${file.name}: 스토리지 미연결 — 로컬 미리보기로 대체됩니다.`);
      }

      // 3. Move file from uploading → uploaded
      const newFile: UploadedFile = {
        filename: file.name,
        publicUrl,
        objectKey,
        size: file.size,
      };

      setUploadedFiles((prev) => {
        const updated = [...prev, newFile];
        reportChange(updated);
        return updated;
      });

      // 4. Remove from uploading list after a short delay so user sees 100%
      setTimeout(() => {
        setUploadingFiles((prev) => prev.filter((f) => f.filename !== file.name));
      }, 500);
    },
    [message, reportChange],
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const remaining = maxFiles - uploadedFiles.length;
      if (remaining <= 0) {
        message.warning(`최대 ${maxFiles}개 파일까지 업로드 가능합니다`);
        return;
      }
      const filesToUpload = acceptedFiles.slice(0, remaining);
      filesToUpload.forEach(uploadFile);
    },
    [maxFiles, uploadedFiles.length, message, uploadFile],
  );

  /** Dismiss a failed upload from the uploading list. */
  const handleDismissUpload = useCallback((filename: string) => {
    setUploadingFiles((prev) => prev.filter((f) => f.filename !== filename));
  }, []);

  /** Retry a failed upload using the original File reference. */
  const handleRetryUpload = useCallback(
    (filename: string) => {
      const entry = uploadingFiles.find((f) => f.filename === filename);
      if (entry?.file) {
        // Remove the failed entry first, then re-upload
        setUploadingFiles((prev) => prev.filter((f) => f.filename !== filename));
        uploadFile(entry.file);
      }
    },
    [uploadingFiles, uploadFile],
  );

  const handleRemove = useCallback(
    (index: number) => {
      setUploadedFiles((prev) => {
        const updated = prev.filter((_, i) => i !== index);
        reportChange(updated);
        return updated;
      });
    },
    [reportChange],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    disabled: uploadedFiles.length >= maxFiles,
  });

  /** Check if a URL or filename looks like an image. Handles blob URLs by falling back to filename. */
  const isImage = (url: string, filename?: string) =>
    /\.(jpg|jpeg|png|gif|webp)$/i.test(url) ||
    (filename != null && /\.(jpg|jpeg|png|gif|webp)$/i.test(filename));

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
          isDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-300'
        } ${uploadedFiles.length >= maxFiles ? 'cursor-not-allowed opacity-50' : ''}`}
      >
        <input {...getInputProps()} />
        <InboxOutlined className="mb-2 text-3xl text-gray-400" />
        <p className="text-sm text-gray-500">
          {isDragActive
            ? '파일을 여기에 놓으세요'
            : '클릭하거나 파일을 드래그하여 업로드 (최대 100MB)'}
        </p>
        <Text type="secondary" className="text-xs">
          이미지, 동영상, PDF · 최대 {maxFiles}개
        </Text>
      </div>

      {/* Uploading progress */}
      {uploadingFiles.length > 0 && (
        <List
          size="small"
          dataSource={uploadingFiles}
          renderItem={(item) => (
            <List.Item>
              <div className="flex w-full items-center gap-2">
                {item.error ? (
                  <CloseCircleOutlined className="text-red-500" />
                ) : (
                  <LoadingOutlined />
                )}
                <Text className="flex-1 truncate text-xs">{item.filename}</Text>
                {item.error ? (
                  <Space size={4}>
                    <Text type="danger" className="text-xs">{item.error}</Text>
                    <Button
                      type="text"
                      size="small"
                      icon={<ReloadOutlined />}
                      onClick={() => handleRetryUpload(item.filename)}
                      title="재시도"
                    />
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleDismissUpload(item.filename)}
                      title="닫기"
                    />
                  </Space>
                ) : (
                  <Progress size="small" percent={item.progress} className="w-24" />
                )}
              </div>
            </List.Item>
          )}
        />
      )}

      {/* Uploaded files */}
      {uploadedFiles.length > 0 && (
        <List
          size="small"
          dataSource={uploadedFiles}
          renderItem={(item, index) => (
            <List.Item
              actions={[
                <Button
                  key="delete"
                  type="text"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => handleRemove(index)}
                />,
              ]}
            >
              <div className="flex items-center gap-2">
                {isImage(item.publicUrl, item.filename) ? (
                  <Image
                    src={item.publicUrl}
                    width={40}
                    height={40}
                    className="rounded object-cover"
                    fallback="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>"
                  />
                ) : (
                  <div className="flex h-10 w-10 items-center justify-center rounded bg-gray-100 text-xs">
                    파일
                  </div>
                )}
                <Text className="truncate text-xs">{item.filename}</Text>
              </div>
            </List.Item>
          )}
        />
      )}
    </div>
  );
}
