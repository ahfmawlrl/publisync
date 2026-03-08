import {
  CommentOutlined,
  FileTextOutlined,
  SearchOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { AutoComplete, Input, Spin, Tag, Typography } from 'antd';
import type { DefaultOptionType } from 'antd/es/select';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';

import { useSearch } from '@/shared/hooks/useSearch';
import type { SearchResultItem } from '@/shared/hooks/useSearch';

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

const TYPE_ICONS: Record<string, React.ReactNode> = {
  content: <FileTextOutlined className="text-gray-400" />,
  comment: <CommentOutlined className="text-gray-400" />,
  user: <UserOutlined className="text-gray-400" />,
};

const TYPE_LABELS: Record<string, string> = {
  content: '콘텐츠',
  comment: '댓글',
  user: '사용자',
};

/** Derive a navigation path from the search result type + id */
function getResultPath(item: SearchResultItem): string {
  switch (item.type) {
    case 'comment':
      return `/comments`;
    case 'user':
      return `/users`;
    default:
      return `/contents/${item.id}`;
  }
}

function renderItem(item: SearchResultItem) {
  return {
    value: item.id,
    label: (
      <div className="flex items-center gap-2 py-1">
        {TYPE_ICONS[item.type] || TYPE_ICONS.content}
        <Text className="flex-1 truncate text-sm">{item.title}</Text>
        {item.status && (
          <Tag color={STATUS_COLOR[item.status] || 'default'} className="text-xs">
            {item.status}
          </Tag>
        )}
      </div>
    ),
  };
}

export default function SearchBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const { data, isLoading } = useSearch(query);

  /** Group results by entity type for AutoComplete option groups */
  const options: DefaultOptionType[] = useMemo(() => {
    if (!data?.data?.length) return [];

    const grouped: Record<string, SearchResultItem[]> = {};
    for (const item of data.data) {
      const type = item.type || 'content';
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push(item);
    }

    return Object.entries(grouped).map(([type, items]) => ({
      label: (
        <span className="text-xs font-semibold text-gray-500">
          {TYPE_LABELS[type] || type}
        </span>
      ),
      options: items.map(renderItem),
    }));
  }, [data]);

  const handleSelect = useCallback(
    (value: string) => {
      const item = data?.data?.find((r) => r.id === value);
      if (item) {
        navigate(getResultPath(item));
      } else {
        navigate(`/contents/${value}`);
      }
      setQuery('');
    },
    [data, navigate],
  );

  const notFoundContent = isLoading ? (
    <div className="flex justify-center py-4">
      <Spin size="small" />
    </div>
  ) : query.length >= 2 ? (
    <div className="py-4 text-center">
      <Text type="secondary">검색 결과가 없습니다</Text>
    </div>
  ) : null;

  return (
    <AutoComplete
      options={options}
      onSelect={handleSelect}
      onSearch={setQuery}
      value={query}
      notFoundContent={notFoundContent}
      popupMatchSelectWidth={360}
      style={{ width: 260 }}
    >
      <Input
        prefix={<SearchOutlined className="text-gray-400" />}
        placeholder="콘텐츠·댓글·사용자 검색..."
        allowClear
        style={{ borderRadius: 20 }}
        aria-label="통합 검색"
      />
    </AutoComplete>
  );
}
