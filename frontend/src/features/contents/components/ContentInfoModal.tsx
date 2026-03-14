/**
 * ContentInfoModal — 콘텐츠 정보 모달 (제목/본문/해시태그/예약 게시).
 *
 * 영상 중심 ContentEditorPage 재설계에서 텍스트 입력은 모달로 분리.
 * 헤더의 [콘텐츠 정보] 버튼 → 이 모달 오픈.
 */

import { RobotOutlined } from '@ant-design/icons';
import {
  Button,
  DatePicker,
  Dropdown,
  Form,
  Input,
  Modal,
  Select,
  Space,
  type FormInstance,
} from 'antd';

import AiSuggestionPanel from '@/features/ai/components/AiSuggestionPanel';
import {
  useGenerateDescription,
  useGenerateHashtags,
  useGenerateTitle,
} from '@/features/ai/hooks/useAi';

const { TextArea } = Input;

interface ContentInfoModalProps {
  open: boolean;
  onClose: () => void;
  form: FormInstance;
}

export default function ContentInfoModal({ open, onClose, form }: ContentInfoModalProps) {
  const titleMutation = useGenerateTitle();
  const descriptionMutation = useGenerateDescription();
  const hashtagMutation = useGenerateHashtags();

  /** 제목 또는 본문 중 하나만 있어도 AI 호출 가능 */
  const getContentText = (): string | null => {
    const title = form.getFieldValue('title') as string | undefined;
    const body = form.getFieldValue('body') as string | undefined;
    const combined = [title, body].filter(Boolean).join('\n').trim();
    if (combined.length < 5) {
      return null;
    }
    return combined;
  };

  const getSelectedPlatform = (): string | undefined => {
    const platforms = form.getFieldValue('platforms') as string[] | undefined;
    return platforms?.[0];
  };

  return (
    <Modal
      title="콘텐츠 정보"
      open={open}
      onCancel={onClose}
      footer={
        <Button type="primary" onClick={onClose}>
          적용
        </Button>
      }
      width={720}
      destroyOnHidden={false}
    >
      <Form form={form} layout="vertical">
      <div className="space-y-4">
        {/* 제목 */}
        <Form.Item
          name="title"
          label="제목"
          rules={[{ required: true, message: '제목을 입력하세요' }]}
        >
          <Input placeholder="콘텐츠 제목" maxLength={500} showCount />
        </Form.Item>

        <div className="flex justify-end">
          <Dropdown
            menu={{
              items: [
                {
                  key: 'title',
                  label: 'AI 제목 제안',
                  icon: <RobotOutlined />,
                  onClick: () => {
                    const text = getContentText();
                    if (text)
                      titleMutation.mutate({
                        content_text: text,
                        platform: getSelectedPlatform(),
                        count: 3,
                      });
                  },
                },
                {
                  key: 'description',
                  label: 'AI 설명문 제안',
                  icon: <RobotOutlined />,
                  onClick: () => {
                    const text = getContentText();
                    if (text)
                      descriptionMutation.mutate({
                        content_text: text,
                        platform: getSelectedPlatform(),
                        count: 2,
                      });
                  },
                },
                {
                  key: 'hashtags',
                  label: 'AI 해시태그 추천',
                  icon: <RobotOutlined />,
                  onClick: () => {
                    const text = getContentText();
                    if (text)
                      hashtagMutation.mutate({
                        content_text: text,
                        platform: getSelectedPlatform(),
                        count: 5,
                      });
                  },
                },
              ],
            }}
            trigger={['click']}
          >
            <Button icon={<RobotOutlined />} loading={titleMutation.isPending || descriptionMutation.isPending || hashtagMutation.isPending}>
              AI 제안
            </Button>
          </Dropdown>
        </div>

        {/* AI 제목 제안 결과 */}
        {(titleMutation.isPending || titleMutation.data || titleMutation.isError) && (
          <AiSuggestionPanel
            title="AI 제목 제안"
            suggestions={titleMutation.data?.suggestions ?? []}
            loading={titleMutation.isPending}
            onSelect={(c) => form.setFieldValue('title', c)}
            error={titleMutation.data?.error ?? (titleMutation.isError ? 'AI 서비스 요청에 실패했습니다.' : undefined)}
            model={titleMutation.data?.model}
            processingTimeMs={titleMutation.data?.processing_time_ms}
          />
        )}

        {/* 본문 */}
        <Form.Item name="body" label="본문/설명문">
          <TextArea rows={6} placeholder="콘텐츠 본문을 작성하세요" />
        </Form.Item>

        {/* AI 설명문 결과 */}
        {(descriptionMutation.isPending || descriptionMutation.data || descriptionMutation.isError) && (
          <AiSuggestionPanel
            title="AI 설명문 제안"
            suggestions={descriptionMutation.data?.suggestions ?? []}
            loading={descriptionMutation.isPending}
            onSelect={(c) => {
              const cur = (form.getFieldValue('body') as string) || '';
              form.setFieldValue('body', cur ? `${cur}\n\n${c}` : c);
            }}
            error={descriptionMutation.data?.error ?? (descriptionMutation.isError ? 'AI 서비스 요청에 실패했습니다.' : undefined)}
            model={descriptionMutation.data?.model}
            processingTimeMs={descriptionMutation.data?.processing_time_ms}
          />
        )}

        {/* 해시태그 */}
        <Form.Item name="hashtags" label="해시태그">
          <Select mode="tags" placeholder="#서울시 #정책브리핑" tokenSeparators={[' ', ',']} />
        </Form.Item>

        {/* AI 해시태그 결과 */}
        {(hashtagMutation.isPending || hashtagMutation.data || hashtagMutation.isError) && (
          <AiSuggestionPanel
            title="AI 해시태그 추천"
            suggestions={hashtagMutation.data?.suggestions ?? []}
            loading={hashtagMutation.isPending}
            onSelect={(c) => {
              const current = (form.getFieldValue('hashtags') as string[]) || [];
              const tags = c.split(/[,\s]+/).filter(Boolean);
              form.setFieldValue('hashtags', [...new Set([...current, ...tags])]);
            }}
            error={hashtagMutation.data?.error ?? (hashtagMutation.isError ? 'AI 서비스 요청에 실패했습니다.' : undefined)}
            model={hashtagMutation.data?.model}
            processingTimeMs={hashtagMutation.data?.processing_time_ms}
          />
        )}

        {/* 예약 게시 */}
        <Form.Item name="scheduled_at" label="예약 게시일시">
          <DatePicker
            showTime
            format="YYYY-MM-DD HH:mm"
            placeholder="예약 게시 (선택)"
            className="w-full"
          />
        </Form.Item>
      </div>
      </Form>
    </Modal>
  );
}
