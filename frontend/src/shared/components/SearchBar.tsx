import { FileTextOutlined, SearchOutlined } from '@ant-design/icons';
import { Input, List, Popover, Spin, Tag, Typography } from 'antd';
import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router';

import { useSearch } from '@/shared/hooks/useSearch';

const { Text } = Typography;

const STATUS_COLOR: Record<string, string> = {
  DRAFT: 'default',
  PENDING_REVIEW: 'orange',
  IN_REVIEW: 'processing',
  APPROVED: 'cyan',
  REJECTED: 'red',
  SCHEDULED: 'blue',
  PUBLISHED: 'green',
};

export default function SearchBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const inputRef = useRef<ReturnType<typeof Input.Search> | null>(null);
  const { data, isLoading } = useSearch(query);

  const handleSelect = useCallback(
    (id: string) => {
      setOpen(false);
      setQuery('');
      navigate(`/contents/${id}`);
    },
    [navigate],
  );

  const searchResults = (
    <div style={{ width: 360, maxHeight: 400, overflow: 'auto' }}>
      {isLoading ? (
        <div className="flex justify-center py-4">
          <Spin size="small" />
        </div>
      ) : data && data.data.length > 0 ? (
        <List
          size="small"
          dataSource={data.data}
          renderItem={(item) => (
            <List.Item
              className="cursor-pointer hover:bg-gray-50"
              onClick={() => handleSelect(item.id)}
            >
              <List.Item.Meta
                avatar={<FileTextOutlined className="mt-1 text-gray-400" />}
                title={
                  <div className="flex items-center gap-2">
                    <Text className="truncate text-sm">{item.title}</Text>
                    <Tag color={STATUS_COLOR[item.status] || 'default'} className="text-xs">
                      {item.status}
                    </Tag>
                  </div>
                }
                description={
                  item.snippet && (
                    <Text type="secondary" className="text-xs">
                      {item.snippet}
                    </Text>
                  )
                }
              />
            </List.Item>
          )}
        />
      ) : query.length >= 2 ? (
        <div className="py-4 text-center">
          <Text type="secondary">검색 결과가 없습니다</Text>
        </div>
      ) : null}
    </div>
  );

  return (
    <Popover
      content={searchResults}
      open={open && query.length >= 2}
      onOpenChange={setOpen}
      trigger="click"
      placement="bottomLeft"
      arrow={false}
    >
      <Input
        ref={inputRef as never}
        prefix={<SearchOutlined className="text-gray-400" />}
        placeholder="콘텐츠 검색..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          if (e.target.value.length >= 2) setOpen(true);
        }}
        onFocus={() => {
          if (query.length >= 2) setOpen(true);
        }}
        allowClear
        style={{ width: 240 }}
        aria-label="통합 검색"
      />
    </Popover>
  );
}
