import { ArrowLeftOutlined } from '@ant-design/icons';
import { App, Button, Card, Checkbox, DatePicker, Form, Input, Space, Spin, Typography } from 'antd';
import dayjs from 'dayjs';
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router';

import { useContent, useUpdateContent } from '../hooks/useContents';

const { Title } = Typography;
const { TextArea } = Input;

const PLATFORM_OPTIONS = [
  { value: 'YOUTUBE', label: 'YouTube' },
  { value: 'INSTAGRAM', label: 'Instagram' },
  { value: 'FACEBOOK', label: 'Facebook' },
  { value: 'X', label: 'X (Twitter)' },
  { value: 'NAVER_BLOG', label: '네이버 블로그' },
];

export default function ContentEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const { data: content, isLoading } = useContent(id ?? null);
  const updateMutation = useUpdateContent();

  useEffect(() => {
    if (content) {
      form.setFieldsValue({
        title: content.title,
        body: content.body,
        platforms: content.platforms,
        scheduled_at: content.scheduled_at ? dayjs(content.scheduled_at) : null,
      });
    }
  }, [content, form]);

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center"><Spin size="large" /></div>;
  }

  if (!content) {
    return <div className="p-6"><Title level={4}>콘텐츠를 찾을 수 없습니다</Title></div>;
  }

  const handleSubmit = async (values: Record<string, unknown>) => {
    if (!id) return;
    try {
      await updateMutation.mutateAsync({
        id,
        data: {
          title: values.title as string,
          body: values.body as string | undefined,
          platforms: (values.platforms as string[]) || [],
          scheduled_at: values.scheduled_at
            ? (values.scheduled_at as { toISOString: () => string }).toISOString()
            : null,
        },
      });
      message.success('콘텐츠가 수정되었습니다');
      navigate(`/contents/${id}`);
    } catch {
      message.error('콘텐츠 수정에 실패했습니다');
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/contents/${id}`)} />
        <Title level={4} className="!mb-0">콘텐츠 수정</Title>
      </div>

      <Card>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="title" label="제목" rules={[{ required: true, message: '제목을 입력하세요' }]}>
            <Input placeholder="콘텐츠 제목" maxLength={500} showCount />
          </Form.Item>

          <Form.Item name="body" label="본문">
            <TextArea rows={10} placeholder="콘텐츠 본문을 작성하세요" />
          </Form.Item>

          <Form.Item name="platforms" label="게시 플랫폼">
            <Checkbox.Group options={PLATFORM_OPTIONS} />
          </Form.Item>

          <Form.Item name="scheduled_at" label="예약 게시일시">
            <DatePicker showTime format="YYYY-MM-DD HH:mm" placeholder="예약 게시 (선택)" className="w-full" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>저장</Button>
              <Button onClick={() => navigate(`/contents/${id}`)}>취소</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
