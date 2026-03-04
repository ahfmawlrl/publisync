import {
  DeleteOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons';
import {
  App,
  Button,
  Descriptions,
  Input,
  List,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';

import { useGenerateReply } from '@/features/ai/hooks/useAi';
import {
  useComments,
  useDeleteRequest,
  useHideComment,
  useReplyComment,
} from '../hooks/useComments';
import type { CommentRecord } from '../types';

const { Title } = Typography;
const { Search } = Input;
const { TextArea } = Input;

const SENTIMENT_CONFIG: Record<string, { color: string; text: string }> = {
  POSITIVE: { color: 'green', text: '긍정' },
  NEUTRAL: { color: 'default', text: '중립' },
  NEGATIVE: { color: 'orange', text: '부정' },
  DANGEROUS: { color: 'red', text: '위험' },
};

const STATUS_CONFIG: Record<string, { color: string; text: string }> = {
  UNPROCESSED: { color: 'default', text: '미처리' },
  PUBLISHED: { color: 'green', text: '답변완료' },
  HIDDEN: { color: 'warning', text: '숨김' },
  PENDING_DELETE: { color: 'orange', text: '삭제대기' },
  DELETED: { color: 'red', text: '삭제됨' },
};

const PLATFORM_COLORS: Record<string, string> = {
  YOUTUBE: 'red',
  INSTAGRAM: 'purple',
  FACEBOOK: 'blue',
  X: 'default',
  NAVER_BLOG: 'green',
};

export default function CommentsListPage() {
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [platformFilter, setPlatformFilter] = useState<string | undefined>();
  const [searchText, setSearchText] = useState<string | undefined>();

  // Detail modal
  const [detailComment, setDetailComment] = useState<CommentRecord | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Reply modal
  const [replyComment, setReplyComment] = useState<CommentRecord | null>(null);
  const [replyOpen, setReplyOpen] = useState(false);
  const [replyText, setReplyText] = useState('');

  const { data, isLoading } = useComments({
    page,
    status: statusFilter,
    platform: platformFilter,
    search: searchText,
  });

  // AI reply modal
  const [aiReplyComment, setAiReplyComment] = useState<CommentRecord | null>(null);
  const [aiReplyOpen, setAiReplyOpen] = useState(false);
  const aiReplyMutation = useGenerateReply();

  const replyMutation = useReplyComment();
  const hideMutation = useHideComment();
  const deleteRequestMutation = useDeleteRequest();

  const handleReplySubmit = () => {
    if (!replyComment || !replyText.trim()) return;
    replyMutation.mutate(
      { id: replyComment.id, text: replyText.trim() },
      {
        onSuccess: () => {
          message.success('댓글에 답변했습니다');
          setReplyOpen(false);
          setReplyText('');
          setReplyComment(null);
        },
        onError: () => message.error('답변 등록에 실패했습니다'),
      },
    );
  };

  const handleAiReplyGenerate = (comment: CommentRecord) => {
    setAiReplyComment(comment);
    setAiReplyOpen(true);
    aiReplyMutation.mutate(
      {
        comment_text: comment.text,
        tone: 'formal',
        count: 3,
      },
      {
        onError: () => message.error('AI 답글 생성에 실패했습니다'),
      },
    );
  };

  const handleAiReplySelect = (content: string) => {
    // Carry over the AI suggestion into the reply modal
    setReplyComment(aiReplyComment);
    setReplyText(content);
    setReplyOpen(true);
    setAiReplyOpen(false);
    setAiReplyComment(null);
  };

  const columns: ColumnsType<CommentRecord> = [
    {
      title: '작성자',
      dataIndex: 'author_name',
      key: 'author_name',
      width: 120,
      ellipsis: true,
    },
    {
      title: '댓글 내용',
      dataIndex: 'text',
      key: 'text',
      ellipsis: true,
      render: (text: string, record) => (
        <a
          onClick={() => {
            setDetailComment(record);
            setDetailOpen(true);
          }}
        >
          {text.length > 80 ? `${text.slice(0, 80)}...` : text}
        </a>
      ),
    },
    {
      title: '플랫폼',
      dataIndex: 'platform',
      key: 'platform',
      width: 110,
      render: (p: string) => <Tag color={PLATFORM_COLORS[p]}>{p}</Tag>,
    },
    {
      title: '감성',
      dataIndex: 'sentiment',
      key: 'sentiment',
      width: 80,
      render: (s: string | null) => {
        if (!s) return '-';
        const cfg = SENTIMENT_CONFIG[s] || { color: 'default', text: s };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const cfg = STATUS_CONFIG[s] || { color: 'default', text: s };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '작성일',
      dataIndex: 'platform_created_at',
      key: 'platform_created_at',
      width: 150,
      render: (v: string | null, record) => {
        const dt = v || record.created_at;
        return new Date(dt).toLocaleString('ko-KR');
      },
    },
    {
      title: '관리',
      key: 'actions',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setDetailComment(record);
              setDetailOpen(true);
            }}
            title="상세"
          />
          <Button
            type="text"
            size="small"
            icon={<SendOutlined />}
            onClick={() => {
              setReplyComment(record);
              setReplyText(record.reply_draft || '');
              setReplyOpen(true);
            }}
            title="답변"
            disabled={record.status === 'DELETED'}
          />
          <Button
            type="text"
            size="small"
            icon={<RobotOutlined />}
            onClick={() => handleAiReplyGenerate(record)}
            title="AI 답글 생성"
            disabled={record.status === 'DELETED'}
          />
          <Popconfirm
            title="이 댓글을 숨기시겠습니까?"
            onConfirm={() => {
              hideMutation.mutate(
                { id: record.id },
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
              type="text"
              size="small"
              icon={<EyeInvisibleOutlined />}
              title="숨기기"
              disabled={!['UNPROCESSED', 'PUBLISHED'].includes(record.status)}
            />
          </Popconfirm>
          <Popconfirm
            title="이 댓글의 삭제를 요청하시겠습니까?"
            onConfirm={() => {
              deleteRequestMutation.mutate(
                { id: record.id },
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
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              title="삭제 요청"
              disabled={['DELETED', 'PENDING_DELETE'].includes(record.status)}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          댓글 관리
        </Title>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <Select
          placeholder="상태 필터"
          allowClear
          style={{ width: 140 }}
          onChange={(v) => {
            setStatusFilter(v);
            setPage(1);
          }}
          options={Object.entries(STATUS_CONFIG).map(([value, { text }]) => ({ value, label: text }))}
        />
        <Select
          placeholder="플랫폼"
          allowClear
          style={{ width: 140 }}
          onChange={(v) => {
            setPlatformFilter(v);
            setPage(1);
          }}
          options={[
            { value: 'YOUTUBE', label: 'YouTube' },
            { value: 'INSTAGRAM', label: 'Instagram' },
            { value: 'FACEBOOK', label: 'Facebook' },
            { value: 'X', label: 'X' },
            { value: 'NAVER_BLOG', label: '네이버 블로그' },
          ]}
        />
        <Select
          placeholder="감성 분석"
          allowClear
          style={{ width: 140 }}
          onChange={() => {
            // Sentiment filter would need backend support via status or separate param
            // For now, this is a UI placeholder
            setPage(1);
          }}
          options={Object.entries(SENTIMENT_CONFIG).map(([value, { text }]) => ({
            value,
            label: text,
          }))}
        />
        <Search
          placeholder="댓글 내용 또는 작성자 검색"
          allowClear
          style={{ width: 280 }}
          onSearch={(v) => {
            setSearchText(v || undefined);
            setPage(1);
          }}
        />
      </div>

      <Table
        columns={columns}
        dataSource={data?.data || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          total: data?.meta?.total || 0,
          pageSize: 20,
          onChange: setPage,
          showTotal: (total) => `총 ${total}개`,
        }}
      />

      {/* Detail Modal */}
      <Modal
        title="댓글 상세"
        open={detailOpen}
        onCancel={() => {
          setDetailOpen(false);
          setDetailComment(null);
        }}
        footer={null}
        width={640}
      >
        {detailComment && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="작성자">{detailComment.author_name}</Descriptions.Item>
            <Descriptions.Item label="댓글 내용">
              <div style={{ whiteSpace: 'pre-wrap' }}>{detailComment.text}</div>
            </Descriptions.Item>
            <Descriptions.Item label="플랫폼">
              <Tag color={PLATFORM_COLORS[detailComment.platform]}>{detailComment.platform}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="감성">
              {detailComment.sentiment ? (
                <Tag
                  color={
                    SENTIMENT_CONFIG[detailComment.sentiment]?.color || 'default'
                  }
                >
                  {SENTIMENT_CONFIG[detailComment.sentiment]?.text || detailComment.sentiment}
                </Tag>
              ) : (
                '-'
              )}
              {detailComment.sentiment_confidence != null && (
                <span className="ml-2 text-gray-500">
                  (신뢰도: {(detailComment.sentiment_confidence * 100).toFixed(1)}%)
                </span>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="상태">
              <Tag color={STATUS_CONFIG[detailComment.status]?.color || 'default'}>
                {STATUS_CONFIG[detailComment.status]?.text || detailComment.status}
              </Tag>
            </Descriptions.Item>
            {detailComment.reply_text && (
              <Descriptions.Item label="답변 내용">
                <div style={{ whiteSpace: 'pre-wrap' }}>{detailComment.reply_text}</div>
              </Descriptions.Item>
            )}
            {detailComment.hidden_reason && (
              <Descriptions.Item label="숨김 사유">{detailComment.hidden_reason}</Descriptions.Item>
            )}
            {detailComment.delete_reason && (
              <Descriptions.Item label="삭제 사유">{detailComment.delete_reason}</Descriptions.Item>
            )}
            <Descriptions.Item label="키워드">
              {detailComment.keywords?.length ? (
                <Space size={2} wrap>
                  {detailComment.keywords.map((kw) => (
                    <Tag key={kw}>{kw}</Tag>
                  ))}
                </Space>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="작성일시">
              {detailComment.platform_created_at
                ? new Date(detailComment.platform_created_at).toLocaleString('ko-KR')
                : new Date(detailComment.created_at).toLocaleString('ko-KR')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* Reply Modal */}
      <Modal
        title="댓글 답변"
        open={replyOpen}
        onCancel={() => {
          setReplyOpen(false);
          setReplyText('');
          setReplyComment(null);
        }}
        onOk={handleReplySubmit}
        okText="답변 등록"
        cancelText="취소"
        confirmLoading={replyMutation.isPending}
      >
        {replyComment && (
          <div className="mb-4">
            <div className="mb-2 rounded bg-gray-50 p-3">
              <div className="mb-1 text-sm font-medium text-gray-600">
                {replyComment.author_name}
              </div>
              <div className="text-sm">{replyComment.text}</div>
            </div>
            <TextArea
              rows={4}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="답변 내용을 입력하세요"
            />
          </div>
        )}
      </Modal>

      {/* AI Reply Generation Modal */}
      <Modal
        title={
          <Space>
            <RobotOutlined />
            <span>AI 답글 생성</span>
          </Space>
        }
        open={aiReplyOpen}
        onCancel={() => {
          setAiReplyOpen(false);
          setAiReplyComment(null);
          aiReplyMutation.reset();
        }}
        footer={null}
        width={640}
      >
        {aiReplyComment && (
          <div>
            <div className="mb-4 rounded bg-gray-50 p-3">
              <div className="mb-1 text-sm font-medium text-gray-600">
                {aiReplyComment.author_name}
              </div>
              <div className="text-sm">{aiReplyComment.text}</div>
            </div>

            {aiReplyMutation.isPending && (
              <div className="flex items-center justify-center py-8">
                <Space>
                  <Spin size="small" />
                  <Typography.Text type="secondary">
                    AI가 답글을 생성하고 있습니다...
                  </Typography.Text>
                </Space>
              </div>
            )}

            {aiReplyMutation.data?.error && (
              <Typography.Text type="danger">
                {aiReplyMutation.data.error}
              </Typography.Text>
            )}

            {aiReplyMutation.data?.suggestions && aiReplyMutation.data.suggestions.length > 0 && (
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <Typography.Text strong>AI 제안 답글</Typography.Text>
                  {aiReplyMutation.data.model && (
                    <Tag color="blue">{aiReplyMutation.data.model}</Tag>
                  )}
                  {aiReplyMutation.data.processing_time_ms !== undefined && (
                    <Typography.Text type="secondary" className="text-xs">
                      {(aiReplyMutation.data.processing_time_ms / 1000).toFixed(1)}s
                    </Typography.Text>
                  )}
                </div>
                <List
                  size="small"
                  dataSource={aiReplyMutation.data.suggestions}
                  renderItem={(item, index) => (
                    <List.Item
                      key={index}
                      actions={[
                        <Button
                          key="use"
                          type="link"
                          size="small"
                          onClick={() => handleAiReplySelect(item.content)}
                        >
                          사용하기
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={<Typography.Text className="text-sm">{item.content}</Typography.Text>}
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
                <Typography.Text type="secondary" className="mt-2 block text-xs">
                  AI가 생성한 제안입니다. 최종 결정은 사용자가 합니다.
                </Typography.Text>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
