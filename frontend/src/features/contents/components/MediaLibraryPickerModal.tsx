import {
  CheckCircleFilled,
  FileOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  SearchOutlined,
  SoundOutlined,
} from '@ant-design/icons';
import { Card, Empty, Input, Modal, Pagination, Select, Spin, Tag, Tooltip, Typography } from 'antd';
import { useState } from 'react';

import AuthImage from '@/shared/components/AuthImage';

import { useMediaList } from '@/features/media/hooks/useMedia';
import type { MediaAssetListItem, MediaType } from '@/features/media/types';

const { Text } = Typography;

const MEDIA_TYPE_OPTIONS = [
  { label: '전체', value: '' },
  { label: '이미지', value: 'IMAGE' },
  { label: '동영상', value: 'VIDEO' },
  { label: '오디오', value: 'AUDIO' },
  { label: '문서', value: 'DOCUMENT' },
];

function getMediaIcon(mediaType: MediaType) {
  switch (mediaType) {
    case 'IMAGE':
      return <PictureOutlined className="text-3xl text-blue-400" />;
    case 'VIDEO':
      return <PlayCircleOutlined className="text-3xl text-red-400" />;
    case 'AUDIO':
      return <SoundOutlined className="text-3xl text-purple-400" />;
    case 'DOCUMENT':
      return <FileOutlined className="text-3xl text-gray-400" />;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface MediaLibraryPickerModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (items: { url: string; filename: string; size: number }[]) => void;
  maxSelect?: number;
}

export default function MediaLibraryPickerModal({
  open,
  onClose,
  onSelect,
  maxSelect = 10,
}: MediaLibraryPickerModalProps) {
  const [page, setPage] = useState(1);
  const [mediaTypeFilter, setMediaTypeFilter] = useState<MediaType | undefined>();
  const [searchText, setSearchText] = useState<string | undefined>();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedItems, setSelectedItems] = useState<Map<string, MediaAssetListItem>>(new Map());

  const { data: mediaData, isLoading } = useMediaList({
    page,
    limit: 12,
    media_type: mediaTypeFilter,
    search: searchText,
  });

  const assets = mediaData?.data || [];
  const total = mediaData?.meta?.total || 0;

  const toggleSelect = (asset: MediaAssetListItem) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(asset.id)) {
        next.delete(asset.id);
        setSelectedItems((m) => {
          const nm = new Map(m);
          nm.delete(asset.id);
          return nm;
        });
      } else {
        if (next.size >= maxSelect) return prev;
        next.add(asset.id);
        setSelectedItems((m) => new Map(m).set(asset.id, asset));
      }
      return next;
    });
  };

  const handleConfirm = () => {
    const items = Array.from(selectedItems.values()).map((asset) => ({
      url: `/media/${asset.id}/download`,
      filename: asset.filename,
      size: asset.file_size,
    }));
    onSelect(items);
    handleClose();
  };

  const handleClose = () => {
    setSelectedIds(new Set());
    setSelectedItems(new Map());
    setPage(1);
    setMediaTypeFilter(undefined);
    setSearchText(undefined);
    onClose();
  };

  const isImage = (mimeType: string) => mimeType.startsWith('image/');

  return (
    <Modal
      title={`미디어 라이브러리에서 선택 (${selectedIds.size}/${maxSelect})`}
      open={open}
      onCancel={handleClose}
      onOk={handleConfirm}
      okText={`선택 완료 (${selectedIds.size}건)`}
      okButtonProps={{ disabled: selectedIds.size === 0 }}
      cancelText="취소"
      width={800}
      destroyOnClose
    >
      {/* Filters */}
      <div className="mb-4 flex gap-2">
        <Select
          value={mediaTypeFilter || ''}
          onChange={(v) => {
            setMediaTypeFilter(v || undefined);
            setPage(1);
          }}
          options={MEDIA_TYPE_OPTIONS}
          style={{ width: 120 }}
        />
        <Input.Search
          placeholder="파일명 검색"
          allowClear
          onSearch={(v) => {
            setSearchText(v || undefined);
            setPage(1);
          }}
          prefix={<SearchOutlined />}
          style={{ width: 240 }}
        />
      </div>

      {/* Grid */}
      <Spin spinning={isLoading}>
        {assets.length === 0 ? (
          <Empty description="미디어 파일이 없습니다" className="py-8" />
        ) : (
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
            {assets.map((asset) => {
              const selected = selectedIds.has(asset.id);
              return (
                <Card
                  key={asset.id}
                  hoverable
                  size="small"
                  className={`relative transition-all ${selected ? 'ring-2 ring-blue-500' : ''}`}
                  onClick={() => toggleSelect(asset)}
                  cover={
                    isImage(asset.mime_type) ? (
                      <div className="flex h-24 items-center justify-center overflow-hidden bg-gray-50">
                        <AuthImage
                          alt={asset.filename}
                          src={`/media/${asset.id}/thumbnail`}
                          className="h-full w-full object-cover"
                          fallback={
                            <div className="flex h-full w-full items-center justify-center">
                              <PictureOutlined className="text-2xl text-gray-300" />
                            </div>
                          }
                        />
                      </div>
                    ) : (
                      <div className="flex h-24 items-center justify-center bg-gray-50">
                        {getMediaIcon(asset.media_type)}
                      </div>
                    )
                  }
                >
                  {selected && (
                    <CheckCircleFilled className="absolute right-2 top-2 z-10 text-lg text-blue-500" />
                  )}
                  <Tooltip title={asset.filename}>
                    <Text ellipsis className="block text-xs">
                      {asset.filename}
                    </Text>
                  </Tooltip>
                  <div className="flex items-center gap-1">
                    <Text type="secondary" className="text-xs">
                      {formatFileSize(asset.file_size)}
                    </Text>
                    <Tag className="text-xs">{asset.media_type}</Tag>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </Spin>

      {/* Pagination */}
      {total > 12 && (
        <div className="mt-4 flex justify-center">
          <Pagination
            current={page}
            total={total}
            pageSize={12}
            onChange={setPage}
            size="small"
            showSizeChanger={false}
          />
        </div>
      )}
    </Modal>
  );
}
