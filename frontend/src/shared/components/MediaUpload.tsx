import { DeleteOutlined, InboxOutlined, LoadingOutlined } from '@ant-design/icons';
import { App, Button, Image, List, Progress, Typography } from 'antd';
import { useCallback, useState } from 'react';
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
}

interface MediaUploadProps {
  value?: string[];
  onChange?: (urls: string[]) => void;
  maxFiles?: number;
}

export default function MediaUpload({ value = [], onChange, maxFiles = 10 }: MediaUploadProps) {
  const { message } = App.useApp();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>(
    value.map((url) => ({ filename: url.split('/').pop() || 'file', publicUrl: url, objectKey: '', size: 0 })),
  );
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);

  const uploadFile = useCallback(
    async (file: File) => {
      const uploadingItem: UploadingFile = { filename: file.name, progress: 0 };
      setUploadingFiles((prev) => [...prev, uploadingItem]);

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

        const { upload_url, object_key, public_url } = presignedRes.data.data;

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

        // 3. Update state
        const newFile: UploadedFile = {
          filename: file.name,
          publicUrl: public_url,
          objectKey: object_key,
          size: file.size,
        };

        setUploadedFiles((prev) => {
          const updated = [...prev, newFile];
          onChange?.(updated.map((f) => f.publicUrl));
          return updated;
        });
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '업로드 실패';
        setUploadingFiles((prev) =>
          prev.map((f) => (f.filename === file.name ? { ...f, error: errorMsg } : f)),
        );
        message.error(`${file.name}: ${errorMsg}`);
      } finally {
        // Remove from uploading list after a short delay
        setTimeout(() => {
          setUploadingFiles((prev) => prev.filter((f) => f.filename !== file.name));
        }, 1000);
      }
    },
    [message, onChange],
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

  const handleRemove = useCallback(
    (index: number) => {
      setUploadedFiles((prev) => {
        const updated = prev.filter((_, i) => i !== index);
        onChange?.(updated.map((f) => f.publicUrl));
        return updated;
      });
    },
    [onChange],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    disabled: uploadedFiles.length >= maxFiles,
  });

  const isImage = (url: string) => /\.(jpg|jpeg|png|gif|webp)$/i.test(url);

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
                <LoadingOutlined />
                <Text className="flex-1 truncate text-xs">{item.filename}</Text>
                {item.error ? (
                  <Text type="danger" className="text-xs">{item.error}</Text>
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
                {isImage(item.publicUrl) ? (
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
