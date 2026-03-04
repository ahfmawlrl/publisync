import {
  CheckOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  SendOutlined,
} from '@ant-design/icons';
import {
  Alert,
  App,
  Button,
  Descriptions,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';

import {
  useApproveDelete,
  useDangerousComments,
  useIgnoreDangerous,
  useReplyComment,
} from '../hooks/useComments';
import type { CommentRecord } from '../types';

const { Title } = Typography;
const { TextArea } = Input;

const PLATFORM_COLORS: Record<string, string> = {
  YOUTUBE: 'red',
  INSTAGRAM: 'purple',
  FACEBOOK: 'blue',
  X: 'default',
  NAVER_BLOG: 'green',
};

const STATUS_CONFIG: Record<string, { color: string; text: string }> = {
  UNPROCESSED: { color: 'default', text: '미처리' },
  PUBLISHED: { color: 'green', text: '답변완료' },
  HIDDEN: { color: 'warning', text: '숨김' },
  PENDING_DELETE: { color: 'orange', text: '삭제대기' },
  DELETED: { color: 'red', text: '삭제됨' },
};

export default function DangerousCommentsPage() {
  const { message } = App.useApp();
  const [page, setPage] = useState(1);

  // Detail modal
  const [detailComment, setDetailComment] = useState<CommentRecord | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Reply modal
  const [replyComment, setReplyComment] = useState<CommentRecord | null>(null);
  const [replyOpen, setReplyOpen] = useState(false);
  const [replyText, setReplyText] = useState('');

  const { data, isLoading } = useDangerousComments({ page });

  const ignoreMutation = useIgnoreDangerous();
  const approveDeleteMutation = useApproveDelete();
  const replyMutation = useReplyComment();

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
          className="text-red-600"
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
      title: '위험도',
      dataIndex: 'dangerous_level',
      key: 'dangerous_level',
      width: 90,
      render: (level: string | null) => (
        <Tag color="red" icon={<ExclamationCircleOutlined />}>
          {level || '위험'}
        </Tag>
      ),
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
      width: 200,
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
          <Popconfirm
            title="이 댓글의 위험 표시를 해제하시겠습니까?"
            onConfirm={() => {
              ignoreMutation.mutate(record.id, {
                onSuccess: () => message.success('위험 표시가 해제되었습니다'),
                onError: () => message.error('위험 해제에 실패했습니다'),
              });
            }}
            okText="해제"
            cancelText="취소"
          >
            <Button type="text" size="small" icon={<CheckOutlined />} title="위험 해제" />
          </Popconfirm>
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
          {record.status === 'PENDING_DELETE' && (
            <Popconfirm
              title="이 댓글의 삭제를 승인하시겠습니까?"
              onConfirm={() => {
                approveDeleteMutation.mutate(record.id, {
                  onSuccess: () => message.success('삭제가 승인되었습니다'),
                  onError: () => message.error('삭제 승인에 실패했습니다'),
                });
              }}
              okText="승인"
              cancelText="취소"
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                title="삭제 승인"
              />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          위험 댓글 관리
        </Title>
      </div>

      <Alert
        message="위험 댓글 모니터링"
        description="AI 감성 분석에 의해 위험으로 분류된 댓글 목록입니다. 댓글을 확인하고 적절한 조치를 취해주세요."
        type="warning"
        showIcon
        icon={<ExclamationCircleOutlined />}
        className="mb-4"
      />

      <Table
        columns={columns}
        dataSource={data?.data || []}
        rowKey="id"
        loading={isLoading}
        rowClassName={() => 'bg-red-50'}
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
        title={
          <Space>
            <ExclamationCircleOutlined className="text-red-500" />
            <span>위험 댓글 상세</span>
          </Space>
        }
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
              <div style={{ whiteSpace: 'pre-wrap', color: '#cf1322' }}>{detailComment.text}</div>
            </Descriptions.Item>
            <Descriptions.Item label="플랫폼">
              <Tag color={PLATFORM_COLORS[detailComment.platform]}>{detailComment.platform}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="위험도">
              <Tag color="red" icon={<ExclamationCircleOutlined />}>
                {detailComment.dangerous_level || '위험'}
              </Tag>
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
            <Descriptions.Item label="키워드">
              {detailComment.keywords?.length ? (
                <Space size={2} wrap>
                  {detailComment.keywords.map((kw) => (
                    <Tag key={kw} color="red">
                      {kw}
                    </Tag>
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
            <div className="mb-2 rounded border border-red-200 bg-red-50 p-3">
              <div className="mb-1 text-sm font-medium text-gray-600">
                {replyComment.author_name}
              </div>
              <div className="text-sm text-red-700">{replyComment.text}</div>
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
    </div>
  );
}
