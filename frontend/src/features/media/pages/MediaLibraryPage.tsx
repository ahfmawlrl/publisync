import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  FileOutlined,
  FolderAddOutlined,
  InboxOutlined,
  LoadingOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  SoundOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  Empty,
  Form,
  Input,
  Modal,
  Pagination,
  Popconfirm,
  Progress,
  Segmented,
  Select,
  Space,
  Spin,
  Tag,
  Tooltip,
  Tree,
  Typography,
} from 'antd';
import type { DataNode } from 'antd/es/tree';
import { useCallback, useMemo, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import VideoPlayer from '@/shared/components/VideoPlayer';
import WaveformViewer from '@/shared/components/WaveformViewer';

import {
  useCreateFolder,
  useDeleteMedia,
  useMediaFolders,
  useMediaList,
  useUpdateMedia,
} from '../hooks/useMedia';
import type { MediaAssetListItem, MediaType, PresignedUploadResult } from '../types';

const { Title, Text } = Typography;
const { Search } = Input;

const MAX_SIZE = 100 * 1024 * 1024; // 100MB

const ACCEPTED_TYPES: Record<string, string[]> = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/gif': ['.gif'],
  'image/webp': ['.webp'],
  'image/svg+xml': ['.svg'],
  'video/mp4': ['.mp4'],
  'video/webm': ['.webm'],
  'video/quicktime': ['.mov'],
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
};

const MEDIA_TYPE_OPTIONS = [
  { value: 'IMAGE', label: '이미지' },
  { value: 'VIDEO', label: '동영상' },
  { value: 'AUDIO', label: '오디오' },
  { value: 'DOCUMENT', label: '문서' },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getMediaIcon(mediaType: MediaType) {
  switch (mediaType) {
    case 'IMAGE':
      return <PictureOutlined className="text-blue-500" />;
    case 'VIDEO':
      return <PlayCircleOutlined className="text-red-500" />;
    case 'AUDIO':
      return <SoundOutlined className="text-purple-500" />;
    case 'DOCUMENT':
      return <FileOutlined className="text-orange-500" />;
    default:
      return <FileOutlined />;
  }
}

interface UploadingItem {
  filename: string;
  progress: number;
  error?: string;
}

export default function MediaLibraryPage() {
  const { message: messageApi } = App.useApp();
  const queryClient = useQueryClient();

  // State
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState<string | number>('grid');
  const [mediaTypeFilter, setMediaTypeFilter] = useState<MediaType | undefined>();
  const [selectedFolderId, setSelectedFolderId] = useState<string | undefined>();
  const [searchText, setSearchText] = useState<string | undefined>();
  const [tagFilter, setTagFilter] = useState<string[]>([]);

  // Modals
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [folderModalOpen, setFolderModalOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<MediaAssetListItem | null>(null);

  // Upload state
  const [uploadingFiles, setUploadingFiles] = useState<UploadingItem[]>([]);

  // Forms
  const [editForm] = Form.useForm();
  const [folderForm] = Form.useForm();

  // Queries
  const { data: mediaData, isLoading } = useMediaList({
    page,
    limit: 20,
    media_type: mediaTypeFilter,
    folder_id: selectedFolderId,
    search: searchText,
    tags: tagFilter.length > 0 ? tagFilter : undefined,
  });

  const { data: folders } = useMediaFolders();
  const updateMutation = useUpdateMedia();
  const deleteMutation = useDeleteMedia();
  const createFolderMutation = useCreateFolder();

  // Build tree data for folder sidebar
  const folderTreeData = useMemo((): DataNode[] => {
    if (!folders) return [];
    const rootNode: DataNode = {
      title: '전체 파일',
      key: 'all',
      children: [],
    };

    const folderMap = new Map<string, DataNode>();
    for (const f of folders) {
      folderMap.set(f.id, { title: f.name, key: f.id, children: [] });
    }

    for (const f of folders) {
      const node = folderMap.get(f.id)!;
      if (f.parent_id && folderMap.has(f.parent_id)) {
        folderMap.get(f.parent_id)!.children!.push(node);
      } else {
        rootNode.children!.push(node);
      }
    }

    return [rootNode];
  }, [folders]);

  // Upload handler
  const uploadFile = useCallback(
    async (file: File) => {
      const uploadingItem: UploadingItem = { filename: file.name, progress: 0 };
      setUploadingFiles((prev) => [...prev, uploadingItem]);

      try {
        // 1. Get presigned URL
        const presignedRes = await apiClient.post<ApiResponse<PresignedUploadResult>>(
          '/media/presigned-upload',
          { filename: file.name, content_type: file.type, file_size: file.size },
        );

        if (!presignedRes.data.success) {
          throw new Error('Presigned URL 발급 실패');
        }

        const { upload_url, object_key } = presignedRes.data.data;

        // 2. Upload to storage
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
            if (xhr.status >= 200 && xhr.status < 300) resolve();
            else reject(new Error(`업로드 실패: ${xhr.status}`));
          };

          xhr.onerror = () => reject(new Error('네트워크 오류'));
          xhr.send(file);
        });

        // 3. Create asset record
        await apiClient.post('/media/upload', {
          filename: file.name,
          original_filename: file.name,
          content_type: file.type,
          object_key,
          file_size: file.size,
          folder_id: selectedFolderId || undefined,
        });

        queryClient.invalidateQueries({ queryKey: ['media'] });
        messageApi.success(`${file.name} 업로드 완료`);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : '업로드 실패';
        setUploadingFiles((prev) =>
          prev.map((f) => (f.filename === file.name ? { ...f, error: errorMsg } : f)),
        );
        messageApi.error(`${file.name}: ${errorMsg}`);
      } finally {
        setTimeout(() => {
          setUploadingFiles((prev) => prev.filter((f) => f.filename !== file.name));
        }, 1500);
      }
    },
    [messageApi, selectedFolderId],
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      acceptedFiles.forEach(uploadFile);
    },
    [uploadFile],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
  });

  // Handlers
  const handleEditOpen = (asset: MediaAssetListItem) => {
    setSelectedAsset(asset);
    editForm.setFieldsValue({
      filename: asset.filename,
      tags: asset.tags,
      folder_id: asset.folder_id,
    });
    setEditModalOpen(true);
  };

  const handleEditSave = async () => {
    if (!selectedAsset) return;
    try {
      const values = await editForm.validateFields();
      await updateMutation.mutateAsync({ id: selectedAsset.id, data: values });
      messageApi.success('미디어 정보가 수정되었습니다');
      setEditModalOpen(false);
    } catch {
      messageApi.error('수정에 실패했습니다');
    }
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () => messageApi.success('미디어가 삭제되었습니다'),
      onError: () => messageApi.error('삭제에 실패했습니다'),
    });
  };

  const handleCreateFolder = async () => {
    try {
      const values = await folderForm.validateFields();
      await createFolderMutation.mutateAsync(values);
      messageApi.success('폴더가 생성되었습니다');
      setFolderModalOpen(false);
      folderForm.resetFields();
    } catch {
      messageApi.error('폴더 생성에 실패했습니다');
    }
  };

  const handleDetailOpen = (asset: MediaAssetListItem) => {
    setSelectedAsset(asset);
    setDetailModalOpen(true);
  };

  const handleFolderSelect = (selectedKeys: React.Key[]) => {
    const key = selectedKeys[0] as string;
    setSelectedFolderId(key === 'all' ? undefined : key);
    setPage(1);
  };

  const isImage = (mimeType: string) => mimeType.startsWith('image/');
  const isVideo = (mediaType: MediaType) => mediaType === 'VIDEO';
  const isAudio = (mediaType: MediaType) => mediaType === 'AUDIO';
  const getMediaDownloadUrl = (id: string) => `/api/v1/media/${id}/download`;

  const assets = mediaData?.data || [];
  const total = mediaData?.meta?.total || 0;

  return (
    <div className="flex gap-4">
      {/* Sidebar: Folder tree */}
      <div className="w-56 shrink-0">
        <div className="mb-2 flex items-center justify-between">
          <Text strong>폴더</Text>
          <Button
            type="text"
            size="small"
            icon={<FolderAddOutlined />}
            onClick={() => setFolderModalOpen(true)}
            title="새 폴더"
          />
        </div>
        <Tree
          treeData={folderTreeData}
          defaultExpandAll
          selectedKeys={selectedFolderId ? [selectedFolderId] : ['all']}
          onSelect={handleFolderSelect}
          className="rounded border p-2"
        />
      </div>

      {/* Main content */}
      <div className="flex-1">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <Title level={4} className="!mb-0">
            미디어 라이브러리
          </Title>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => setUploadModalOpen(true)}
          >
            업로드
          </Button>
        </div>

        {/* Filters */}
        <div className="mb-4 flex items-center gap-3">
          <Segmented
            value={viewMode}
            onChange={setViewMode}
            options={[
              { value: 'grid', label: '그리드' },
              { value: 'list', label: '리스트' },
            ]}
          />
          <Select
            placeholder="미디어 유형"
            allowClear
            style={{ width: 140 }}
            onChange={(v) => {
              setMediaTypeFilter(v);
              setPage(1);
            }}
            options={MEDIA_TYPE_OPTIONS}
          />
          <Select
            mode="tags"
            placeholder="태그 필터"
            style={{ width: 200 }}
            value={tagFilter}
            onChange={(v) => {
              setTagFilter(v);
              setPage(1);
            }}
          />
          <Search
            placeholder="파일명 검색"
            allowClear
            style={{ width: 240 }}
            onSearch={(v) => {
              setSearchText(v || undefined);
              setPage(1);
            }}
          />
        </div>

        {/* Content area */}
        <Spin spinning={isLoading}>
          {assets.length === 0 ? (
            <Empty description="미디어 파일이 없습니다" className="py-16" />
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
              {assets.map((asset) => (
                <Card
                  key={asset.id}
                  hoverable
                  size="small"
                  cover={
                    isImage(asset.mime_type) ? (
                      <div className="flex h-32 items-center justify-center overflow-hidden bg-gray-50">
                        <img
                          alt={asset.filename}
                          src={`/api/v1/media/${asset.id}/thumbnail`}
                          className="h-full w-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                            (e.target as HTMLImageElement).parentElement!.innerHTML =
                              '<div class="flex h-full w-full items-center justify-center text-3xl text-gray-300"><span>&#128247;</span></div>';
                          }}
                        />
                      </div>
                    ) : (
                      <div className="flex h-32 items-center justify-center bg-gray-50 text-4xl">
                        {getMediaIcon(asset.media_type)}
                      </div>
                    )
                  }
                  actions={[
                    <Tooltip key="detail" title="상세">
                      <EyeOutlined onClick={() => handleDetailOpen(asset)} />
                    </Tooltip>,
                    <Tooltip key="edit" title="수정">
                      <EditOutlined onClick={() => handleEditOpen(asset)} />
                    </Tooltip>,
                    <Popconfirm
                      key="delete"
                      title="이 미디어를 삭제하시겠습니까?"
                      onConfirm={() => handleDelete(asset.id)}
                      okText="삭제"
                      cancelText="취소"
                    >
                      <DeleteOutlined />
                    </Popconfirm>,
                  ]}
                >
                  <Card.Meta
                    title={
                      <Tooltip title={asset.filename}>
                        <Text ellipsis className="text-xs">
                          {asset.filename}
                        </Text>
                      </Tooltip>
                    }
                    description={
                      <Space size={4} wrap>
                        <Text type="secondary" className="text-xs">
                          {formatFileSize(asset.file_size)}
                        </Text>
                        {asset.tags.slice(0, 2).map((tag) => (
                          <Tag key={tag} className="text-xs">
                            {tag}
                          </Tag>
                        ))}
                      </Space>
                    }
                  />
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {assets.map((asset) => (
                <Card key={asset.id} size="small" hoverable>
                  <div className="flex items-center gap-4">
                    <div className="text-2xl">{getMediaIcon(asset.media_type)}</div>
                    <div className="flex-1">
                      <Text strong className="text-sm">
                        {asset.filename}
                      </Text>
                      <br />
                      <Text type="secondary" className="text-xs">
                        {asset.original_filename} / {formatFileSize(asset.file_size)} /{' '}
                        {new Date(asset.created_at).toLocaleDateString('ko-KR')}
                      </Text>
                    </div>
                    <Space size={4} wrap>
                      {asset.tags.map((tag) => (
                        <Tag key={tag}>{tag}</Tag>
                      ))}
                    </Space>
                    <Space>
                      <Button
                        type="text"
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => handleDetailOpen(asset)}
                        title="상세"
                      />
                      <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEditOpen(asset)}
                        title="수정"
                      />
                      <Popconfirm
                        title="이 미디어를 삭제하시겠습니까?"
                        onConfirm={() => handleDelete(asset.id)}
                        okText="삭제"
                        cancelText="취소"
                      >
                        <Button
                          type="text"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          title="삭제"
                        />
                      </Popconfirm>
                    </Space>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </Spin>

        {/* Pagination */}
        {total > 0 && (
          <div className="mt-4 flex justify-end">
            <Pagination
              current={page}
              total={total}
              pageSize={20}
              onChange={setPage}
              showTotal={(t) => `${t}개`}
              showSizeChanger={false}
            />
          </div>
        )}
      </div>

      {/* Upload Modal */}
      <Modal
        title="미디어 업로드"
        open={uploadModalOpen}
        onCancel={() => setUploadModalOpen(false)}
        footer={
          <Button onClick={() => setUploadModalOpen(false)}>닫기</Button>
        }
        width={540}
      >
        <div className="space-y-4">
          <div
            {...getRootProps()}
            className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
              isDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-300'
            }`}
          >
            <input {...getInputProps()} />
            <InboxOutlined className="mb-2 text-4xl text-gray-400" />
            <p className="text-sm text-gray-600">
              {isDragActive
                ? '파일을 여기에 놓으세요'
                : '클릭하거나 파일을 드래그하여 업로드'}
            </p>
            <Text type="secondary" className="text-xs">
              이미지, 동영상, PDF / 최대 100MB
            </Text>
          </div>

          {uploadingFiles.length > 0 && (
            <div className="space-y-2">
              {uploadingFiles.map((item) => (
                <div key={item.filename} className="flex items-center gap-2">
                  <LoadingOutlined />
                  <Text className="flex-1 truncate text-xs">{item.filename}</Text>
                  {item.error ? (
                    <Text type="danger" className="text-xs">
                      {item.error}
                    </Text>
                  ) : (
                    <Progress size="small" percent={item.progress} className="w-28" />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title="미디어 정보 수정"
        open={editModalOpen}
        onOk={handleEditSave}
        onCancel={() => setEditModalOpen(false)}
        okText="저장"
        cancelText="취소"
        confirmLoading={updateMutation.isPending}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="filename"
            label="파일명"
            rules={[{ required: true, message: '파일명을 입력해주세요' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="tags" label="태그">
            <Select mode="tags" placeholder="태그 입력 후 Enter" />
          </Form.Item>
          <Form.Item name="folder_id" label="폴더">
            <Select
              allowClear
              placeholder="폴더 선택"
              options={
                folders?.map((f) => ({ value: f.id, label: f.name })) || []
              }
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="미디어 상세"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={<Button onClick={() => setDetailModalOpen(false)}>닫기</Button>}
        width={600}
      >
        {selectedAsset && (
          <div className="space-y-3">
            {/* Image preview */}
            {isImage(selectedAsset.mime_type) && (
              <div className="flex justify-center rounded bg-gray-50 p-4">
                <img
                  alt={selectedAsset.filename}
                  src={`/api/v1/media/${selectedAsset.id}/thumbnail`}
                  className="max-h-64 object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
            )}
            {/* Video preview */}
            {isVideo(selectedAsset.media_type) && (
              <div className="overflow-hidden rounded bg-gray-50">
                <VideoPlayer
                  src={getMediaDownloadUrl(selectedAsset.id)}
                  type={selectedAsset.mime_type}
                />
              </div>
            )}
            {/* Audio preview */}
            {isAudio(selectedAsset.media_type) && (
              <div className="rounded bg-gray-50 p-4">
                <WaveformViewer
                  audioUrl={getMediaDownloadUrl(selectedAsset.id)}
                  height={80}
                />
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <Text type="secondary">파일명</Text>
                <br />
                <Text>{selectedAsset.filename}</Text>
              </div>
              <div>
                <Text type="secondary">원본 파일명</Text>
                <br />
                <Text>{selectedAsset.original_filename}</Text>
              </div>
              <div>
                <Text type="secondary">파일 크기</Text>
                <br />
                <Text>{formatFileSize(selectedAsset.file_size)}</Text>
              </div>
              <div>
                <Text type="secondary">미디어 유형</Text>
                <br />
                <Text>{selectedAsset.media_type}</Text>
              </div>
              <div>
                <Text type="secondary">MIME 타입</Text>
                <br />
                <Text>{selectedAsset.mime_type}</Text>
              </div>
              <div>
                <Text type="secondary">버전</Text>
                <br />
                <Text>{selectedAsset.version}</Text>
              </div>
              {selectedAsset.width && selectedAsset.height && (
                <div>
                  <Text type="secondary">해상도</Text>
                  <br />
                  <Text>
                    {selectedAsset.width} x {selectedAsset.height}
                  </Text>
                </div>
              )}
              {selectedAsset.duration && (
                <div>
                  <Text type="secondary">재생 시간</Text>
                  <br />
                  <Text>{selectedAsset.duration.toFixed(1)}초</Text>
                </div>
              )}
              <div>
                <Text type="secondary">업로드일</Text>
                <br />
                <Text>{new Date(selectedAsset.created_at).toLocaleString('ko-KR')}</Text>
              </div>
              <div>
                <Text type="secondary">수정일</Text>
                <br />
                <Text>{new Date(selectedAsset.updated_at).toLocaleString('ko-KR')}</Text>
              </div>
            </div>
            {selectedAsset.tags.length > 0 && (
              <div>
                <Text type="secondary">태그</Text>
                <br />
                <Space size={4} wrap className="mt-1">
                  {selectedAsset.tags.map((tag) => (
                    <Tag key={tag}>{tag}</Tag>
                  ))}
                </Space>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Create Folder Modal */}
      <Modal
        title="새 폴더 만들기"
        open={folderModalOpen}
        onOk={handleCreateFolder}
        onCancel={() => {
          setFolderModalOpen(false);
          folderForm.resetFields();
        }}
        okText="생성"
        cancelText="취소"
        confirmLoading={createFolderMutation.isPending}
      >
        <Form form={folderForm} layout="vertical">
          <Form.Item
            name="name"
            label="폴더명"
            rules={[{ required: true, message: '폴더명을 입력해주세요' }]}
          >
            <Input maxLength={255} placeholder="폴더명 입력" />
          </Form.Item>
          <Form.Item name="parent_id" label="상위 폴더">
            <Select
              allowClear
              placeholder="최상위"
              options={
                folders?.map((f) => ({ value: f.id, label: f.name })) || []
              }
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
