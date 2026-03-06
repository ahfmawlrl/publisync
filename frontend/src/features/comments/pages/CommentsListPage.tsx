import {
  DeleteOutlined,
  EyeInvisibleOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  Empty,
  Input,
  List,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';

import { useGenerateReply } from '@/features/ai/hooks/useAi';
import {
  useComments,
  useDeleteRequest,
  useHideComment,
  useReplyComment,
} from '../hooks/useComments';
import type { CommentRecord } from '../types';

const { Title, Text } = Typography;
const { Search } = Input;
const { TextArea } = Input;

const SENTIMENT_CONFIG: Record<string, { color: string; text: string; dot: string }> = {
  POSITIVE: { color: 'green', text: '긍정', dot: '#52c41a' },
  NEUTRAL: { color: 'default', text: '중립', dot: '#faad14' },
  NEGATIVE: { color: 'orange', text: '부정', dot: '#fa8c16' },
  DANGEROUS: { color: 'red', text: '위험', dot: '#ff4d4f' },
};

const PLATFORM_COLORS: Record<string, string> = {
  YOUTUBE: 'red',
  INSTAGRAM: 'purple',
  FACEBOOK: 'blue',
  X: 'default',
  NAVER_BLOG: 'green',
};

const PLATFORM_SHORT: Record<string, string> = {
  YOUTUBE: 'YT',
  INSTAGRAM: 'IG',
  FACEBOOK: 'FB',
  X: 'X',
  NAVER_BLOG: 'Blog',
};

type SentimentTab = 'all' | 'DANGEROUS' | 'NEGATIVE' | 'NEUTRAL' | 'POSITIVE';

export default function CommentsListPage() {
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [sentimentTab, setSentimentTab] = useState<SentimentTab>('all');
  const [platformFilter, setPlatformFilter] = useState<string | undefined>();
  const [searchText, setSearchText] = useState<string | undefined>();
  const [selectedComment, setSelectedComment] = useState<CommentRecord | null>(null);

  // Reply
  const [replyText, setReplyText] = useState('');

  // AI reply
  const [aiReplyOpen, setAiReplyOpen] = useState(false);
  const aiReplyMutation = useGenerateReply();

  const { data, isLoading } = useComments({
    page,
    platform: platformFilter,
    search: searchText,
    sentiment: sentimentTab === 'all' ? undefined : sentimentTab,
  });

  const replyMutation = useReplyComment();
  const hideMutation = useHideComment();
  const deleteRequestMutation = useDeleteRequest();

  const items = data?.data || [];
  const totalCount = data?.meta?.total ?? 0;

  const handleReplySubmit = () => {
    if (!selectedComment || !replyText.trim()) return;
    replyMutation.mutate(
      { id: selectedComment.id, text: replyText.trim() },
      {
        onSuccess: () => {
          message.success('댓글에 답변했습니다');
          setReplyText('');
        },
        onError: () => message.error('답변 등록에 실패했습니다'),
      },
    );
  };

  const handleAiReply = () => {
    if (!selectedComment) return;
    setAiReplyOpen(true);
    aiReplyMutation.mutate(
      { comment_text: selectedComment.text, tone: 'formal', count: 3 },
      { onError: () => message.error('AI 답글 생성에 실패했습니다') },
    );
  };

  const handleAiReplySelect = (content: string) => {
    setReplyText(content);
    setAiReplyOpen(false);
    aiReplyMutation.reset();
  };

  const formatTime = (comment: CommentRecord) => {
    const dt = comment.platform_created_at || comment.created_at;
    const diff = Date.now() - new Date(dt).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}분 전`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}시간 전`;
    return new Date(dt).toLocaleDateString('ko-KR');
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">통합 댓글함</Title>
        <Text type="secondary" className="text-sm">총 {totalCount.toLocaleString()}건</Text>
      </div>

      <Tabs
        activeKey={sentimentTab}
        onChange={(key) => { setSentimentTab(key as SentimentTab); setPage(1); setSelectedComment(null); }}
        items={[
          { key: 'all', label: '전체' },
          { key: 'DANGEROUS', label: '🔴 위험' },
          { key: 'NEGATIVE', label: '🟠 부정' },
          { key: 'NEUTRAL', label: '🟡 중립' },
          { key: 'POSITIVE', label: '🟢 긍정' },
        ]}
      />

      <div className="mb-4 flex items-center gap-3">
        <Select
          placeholder="전체 플랫폼"
          allowClear
          style={{ width: 140 }}
          onChange={(v) => { setPlatformFilter(v); setPage(1); }}
          options={[
            { value: 'YOUTUBE', label: 'YouTube' },
            { value: 'INSTAGRAM', label: 'Instagram' },
            { value: 'FACEBOOK', label: 'Facebook' },
            { value: 'X', label: 'X' },
            { value: 'NAVER_BLOG', label: '네이버 블로그' },
          ]}
        />
        <Search
          placeholder="검색..."
          allowClear
          style={{ width: 240 }}
          onSearch={(v) => { setSearchText(v || undefined); setPage(1); }}
        />
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center"><Spin /></div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Left: Comment list */}
          <div className="max-h-[600px] overflow-y-auto rounded-lg border border-gray-200">
            {items.length > 0 ? items.map((comment) => {
              const isSelected = selectedComment?.id === comment.id;
              const sentimentDot = SENTIMENT_CONFIG[comment.sentiment ?? '']?.dot ?? '#d9d9d9';
              return (
                <div
                  key={comment.id}
                  className={`flex cursor-pointer gap-3 border-b border-gray-100 px-4 py-3 transition-colors ${
                    isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'
                  }`}
                  onClick={() => { setSelectedComment(comment); setReplyText(comment.reply_draft || ''); }}
                >
                  <div
                    className="mt-2 h-2.5 w-2.5 flex-shrink-0 rounded-full"
                    style={{ backgroundColor: sentimentDot }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <Text strong className="text-sm">{comment.author_name}</Text>
                      <Tag
                        color={PLATFORM_COLORS[comment.platform]}
                        className="!text-[10px] !leading-none"
                        style={{ padding: '1px 4px', margin: 0 }}
                      >
                        {PLATFORM_SHORT[comment.platform] || comment.platform}
                      </Tag>
                      <Text type="secondary" className="!text-[11px]">{formatTime(comment)}</Text>
                    </div>
                    <div className="mt-0.5 truncate text-[13px] text-gray-700">
                      {comment.text}
                    </div>
                  </div>
                </div>
              );
            }) : (
              <div className="flex h-64 items-center justify-center">
                <Empty description="댓글이 없습니다" />
              </div>
            )}
            {totalCount > 20 && (
              <div className="flex items-center justify-center gap-2 border-t border-gray-200 py-3">
                <Button size="small" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>이전</Button>
                <Text type="secondary" className="text-xs">페이지 {page}</Text>
                <Button size="small" disabled={items.length < 20} onClick={() => setPage((p) => p + 1)}>다음</Button>
              </div>
            )}
          </div>

          {/* Right: Comment detail */}
          <div>
            {selectedComment ? (
              <Card>
                {/* Post reference */}
                <div className="mb-3 text-sm text-gray-500">
                  📹 원본 게시물 (콘텐츠 ID: {selectedComment.content_id?.slice(0, 8) ?? '-'})
                </div>

                {/* Comment detail */}
                <div
                  className="mb-4 rounded-lg p-3"
                  style={{
                    backgroundColor:
                      selectedComment.sentiment === 'DANGEROUS' ? '#fff2f0' :
                      selectedComment.sentiment === 'NEGATIVE' ? '#fff7e6' : '#f6ffed',
                  }}
                >
                  <div className="mb-1 flex items-center justify-between">
                    <Text strong>
                      {selectedComment.sentiment === 'DANGEROUS' ? '🔴 ' : ''}
                      {selectedComment.author_name}
                    </Text>
                    <Text type="secondary" className="text-xs">{formatTime(selectedComment)}</Text>
                  </div>
                  <div className="my-2 text-sm">{selectedComment.text}</div>
                  <div className="text-xs text-gray-500">
                    감성:{' '}
                    <Tag
                      color={SENTIMENT_CONFIG[selectedComment.sentiment ?? '']?.color}
                      className="!text-xs"
                    >
                      {SENTIMENT_CONFIG[selectedComment.sentiment ?? '']?.text ?? '미분석'}
                    </Tag>
                    {selectedComment.sentiment_confidence != null && (
                      <span>(신뢰도 {(selectedComment.sentiment_confidence * 100).toFixed(0)}%)</span>
                    )}
                    {selectedComment.keywords?.length ? (
                      <span> · 키워드: {selectedComment.keywords.join(', ')}</span>
                    ) : null}
                  </div>
                </div>

                {/* AI reply */}
                <div className="mb-4">
                  <Button
                    icon={<RobotOutlined />}
                    onClick={handleAiReply}
                    loading={aiReplyMutation.isPending}
                    className="mb-2"
                  >
                    AI 답글 생성
                  </Button>
                </div>

                {/* Reply input */}
                <TextArea
                  rows={3}
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="답변 내용을 입력하세요..."
                  className="mb-3"
                />

                <div className="flex items-center justify-between">
                  <Space>
                    <Popconfirm
                      title="이 댓글을 숨기시겠습니까?"
                      onConfirm={() => {
                        hideMutation.mutate(
                          { id: selectedComment.id },
                          {
                            onSuccess: () => message.success('댓글이 숨김 처리되었습니다'),
                            onError: () => message.error('숨김 처리에 실패했습니다'),
                          },
                        );
                      }}
                      okText="숨기기"
                      cancelText="취소"
                    >
                      <Button
                        size="small"
                        icon={<EyeInvisibleOutlined />}
                        disabled={!['UNPROCESSED', 'PUBLISHED'].includes(selectedComment.status)}
                      >
                        숨김 처리
                      </Button>
                    </Popconfirm>
                    <Popconfirm
                      title="이 댓글의 삭제를 요청하시겠습니까?"
                      onConfirm={() => {
                        deleteRequestMutation.mutate(
                          { id: selectedComment.id },
                          {
                            onSuccess: () => message.success('삭제 요청이 등록되었습니다'),
                            onError: () => message.error('삭제 요청에 실패했습니다'),
                          },
                        );
                      }}
                      okText="요청"
                      cancelText="취소"
                    >
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        disabled={['DELETED', 'PENDING_DELETE'].includes(selectedComment.status)}
                      >
                        삭제 승인 요청
                      </Button>
                    </Popconfirm>
                  </Space>
                  <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleReplySubmit}
                    loading={replyMutation.isPending}
                    disabled={!replyText.trim() || selectedComment.status === 'DELETED'}
                  >
                    답글 게시
                  </Button>
                </div>
              </Card>
            ) : (
              <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-gray-300">
                <Text type="secondary">왼쪽에서 댓글을 선택하세요</Text>
              </div>
            )}
          </div>
        </div>
      )}

      {/* AI Reply Modal */}
      <Modal
        title={<Space><RobotOutlined /><span>AI 답글 생성</span></Space>}
        open={aiReplyOpen}
        onCancel={() => { setAiReplyOpen(false); aiReplyMutation.reset(); }}
        footer={null}
        width={640}
      >
        {aiReplyMutation.isPending && (
          <div className="flex items-center justify-center py-8">
            <Space>
              <Spin size="small" />
              <Text type="secondary">AI가 답글을 생성하고 있습니다...</Text>
            </Space>
          </div>
        )}
        {aiReplyMutation.data?.error && (
          <Text type="danger">{aiReplyMutation.data.error}</Text>
        )}
        {aiReplyMutation.data?.suggestions && aiReplyMutation.data.suggestions.length > 0 && (
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Text strong>AI 제안 답글</Text>
              {aiReplyMutation.data.model && <Tag color="blue">{aiReplyMutation.data.model}</Tag>}
            </div>
            <List
              size="small"
              dataSource={aiReplyMutation.data.suggestions}
              renderItem={(item, index) => (
                <List.Item
                  key={index}
                  actions={[
                    <Button key="use" type="link" size="small" onClick={() => handleAiReplySelect(item.content)}>
                      사용하기
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={<Text className="text-sm">{item.content}</Text>}
                    description={
                      <Progress
                        percent={Math.round(item.score * 100)}
                        size="small"
                        className="!mb-0 w-24"
                        format={(p) => `${p}%`}
                      />
                    }
                  />
                </List.Item>
              )}
            />
            <Text type="secondary" className="mt-2 block text-xs">
              AI가 생성한 제안입니다. 최종 결정은 사용자가 합니다.
            </Text>
          </div>
        )}
      </Modal>
    </div>
  );
}
