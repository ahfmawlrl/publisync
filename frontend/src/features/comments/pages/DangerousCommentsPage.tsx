import {
  CheckOutlined,
  DeleteOutlined,
  EyeInvisibleOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import {
  App,
  Button,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Spin,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';

import {
  useApproveDelete,
  useDangerousComments,
  useHideComment,
  useIgnoreDangerous,
  useReplyComment,
} from '../hooks/useComments';
import type { CommentRecord } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const PLATFORM_SHORT: Record<string, string> = {
  YOUTUBE: 'YouTube',
  INSTAGRAM: 'Instagram',
  FACEBOOK: 'Facebook',
  X: 'X',
  NAVER_BLOG: '네이버 블로그',
};

type DangerTab = 'unprocessed' | 'processed' | 'archived';

export default function DangerousCommentsPage() {
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState<DangerTab>('unprocessed');

  // Reply modal
  const [replyComment, setReplyComment] = useState<CommentRecord | null>(null);
  const [replyOpen, setReplyOpen] = useState(false);
  const [replyText, setReplyText] = useState('');

  const statusMap: Record<DangerTab, string | undefined> = {
    unprocessed: 'UNPROCESSED',
    processed: 'PUBLISHED',
    archived: 'HIDDEN',
  };

  const { data, isLoading } = useDangerousComments({ page, status: statusMap[activeTab] });

  const ignoreMutation = useIgnoreDangerous();
  const approveDeleteMutation = useApproveDelete();
  const hideMutation = useHideComment();
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

  const items = data?.data || [];
  const pendingCount = items.filter((i) => i.status === 'UNPROCESSED').length;

  const formatTime = (comment: CommentRecord) => {
    const dt = comment.platform_created_at || comment.created_at;
    const diff = Date.now() - new Date(dt).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}분 전`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}시간 전`;
    return new Date(dt).toLocaleDateString('ko-KR');
  };

  const renderDangerCard = (comment: CommentRecord) => {
    const confidence = comment.sentiment_confidence != null
      ? (comment.sentiment_confidence * 100).toFixed(0)
      : null;
    const isUrgent = confidence != null && Number(confidence) >= 80;

    return (
      <div
        key={comment.id}
        className="mb-3 rounded-lg border-l-4 bg-white p-4 shadow-sm"
        style={{
          borderLeftColor: isUrgent ? '#ff4d4f' : '#faad14',
        }}
      >
        <div className="mb-2 flex items-center gap-2">
          <Tag color={isUrgent ? 'red' : 'gold'}>{isUrgent ? '긴급' : '주의'}</Tag>
          <Text type="secondary" className="text-xs">
            {formatTime(comment)} · {PLATFORM_SHORT[comment.platform] || comment.platform}
            {comment.content_id && ` · 콘텐츠 ${comment.content_id.slice(0, 8)}`}
          </Text>
        </div>
        <div className="my-2 text-sm">
          <Text strong>{comment.author_name}</Text>: &quot;{comment.text}&quot;
        </div>
        <div className="mb-2 text-xs text-gray-500">
          감성: 위험{confidence ? ` (${confidence}%)` : ''}
          {comment.keywords?.length ? ` · 키워드: ${comment.keywords.join(', ')}` : ''}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="small"
            icon={<RobotOutlined />}
            onClick={() => {
              setReplyComment(comment);
              setReplyText('');
              setReplyOpen(true);
            }}
          >
            AI 답글 생성
          </Button>
          <Popconfirm
            title="이 댓글을 숨기시겠습니까?"
            onConfirm={() => {
              hideMutation.mutate(
                { id: comment.id },
                {
                  onSuccess: () => message.success('댓글이 숨김 처리되었습니다'),
                  onError: () => message.error('숨김 처리에 실패했습니다'),
                },
              );
            }}
            okText="숨기기"
            cancelText="취소"
          >
            <Button size="small" icon={<EyeInvisibleOutlined />}>숨김 처리</Button>
          </Popconfirm>
          <Popconfirm
            title="이 댓글의 삭제를 승인하시겠습니까?"
            onConfirm={() => {
              approveDeleteMutation.mutate(comment.id, {
                onSuccess: () => message.success('삭제 요청이 등록되었습니다'),
                onError: () => message.error('삭제 요청에 실패했습니다'),
              });
            }}
            okText="요청"
            cancelText="취소"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>삭제 승인 요청</Button>
          </Popconfirm>
          <Popconfirm
            title="이 댓글의 위험 표시를 해제하시겠습니까?"
            onConfirm={() => {
              ignoreMutation.mutate(comment.id, {
                onSuccess: () => message.success('위험 표시가 해제되었습니다'),
                onError: () => message.error('위험 해제에 실패했습니다'),
              });
            }}
            okText="해제"
            cancelText="취소"
          >
            <Button size="small" icon={<CheckOutlined />}>무시</Button>
          </Popconfirm>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">⚠️ 위험 댓글 관리</Title>
        {pendingCount > 0 && (
          <Text style={{ color: '#ff4d4f', fontWeight: 600 }}>🔴 {pendingCount}건 대기</Text>
        )}
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={(key) => { setActiveTab(key as DangerTab); setPage(1); }}
        items={[
          { key: 'unprocessed', label: '미처리' },
          { key: 'processed', label: '처리 완료' },
          { key: 'archived', label: '아카이브' },
        ]}
      />

      {isLoading ? (
        <div className="flex h-64 items-center justify-center"><Spin /></div>
      ) : items.length > 0 ? (
        <div>
          {items.map(renderDangerCard)}
          {(data?.meta?.total ?? 0) > 20 && (
            <div className="mt-4 text-center">
              <Button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="mr-2">이전</Button>
              <Text type="secondary">페이지 {page}</Text>
              <Button disabled={items.length < 20} onClick={() => setPage((p) => p + 1)} className="ml-2">다음</Button>
            </div>
          )}
        </div>
      ) : (
        <Empty description="위험 댓글이 없습니다" />
      )}

      {/* Reply Modal */}
      <Modal
        title="댓글 답변"
        open={replyOpen}
        onCancel={() => { setReplyOpen(false); setReplyText(''); setReplyComment(null); }}
        onOk={handleReplySubmit}
        okText="답변 등록"
        cancelText="취소"
        confirmLoading={replyMutation.isPending}
      >
        {replyComment && (
          <div className="mb-4">
            <div className="mb-2 rounded border border-red-200 bg-red-50 p-3">
              <div className="mb-1 text-sm font-medium text-gray-600">{replyComment.author_name}</div>
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
