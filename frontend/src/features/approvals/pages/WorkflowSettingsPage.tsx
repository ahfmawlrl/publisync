import { App, Button, Card, Empty, Form, Input, List, Switch, Typography } from 'antd';

import { useUpdateWorkflow, useWorkflows } from '../hooks/useApprovals';

const { Title, Text } = Typography;

export default function WorkflowSettingsPage() {
  const { message } = App.useApp();
  const { data: workflows, isLoading } = useWorkflows();
  const updateMutation = useUpdateWorkflow();
  const [form] = Form.useForm();

  const handleSave = async (values: Record<string, unknown>) => {
    try {
      await updateMutation.mutateAsync({
        name: values.name as string,
        is_active: values.is_active as boolean,
      });
      message.success('워크플로우가 저장되었습니다');
    } catch {
      message.error('워크플로우 저장에 실패했습니다');
    }
  };

  return (
    <div>
      <Title level={4} className="!mb-4">워크플로우 설정</Title>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="현재 워크플로우" loading={isLoading}>
          {workflows && workflows.length > 0 ? (
            <List
              dataSource={workflows}
              renderItem={(wf) => (
                <List.Item>
                  <List.Item.Meta
                    title={wf.name}
                    description={`활성: ${wf.is_active ? '예' : '아니오'} · 단계: ${wf.steps?.length ?? 0}개`}
                  />
                </List.Item>
              )}
            />
          ) : (
            <Empty description="설정된 워크플로우가 없습니다" />
          )}
        </Card>

        <Card title="워크플로우 편집">
          <Form form={form} layout="vertical" onFinish={handleSave} initialValues={{ is_active: true }}>
            <Form.Item name="name" label="워크플로우 이름" rules={[{ required: true, message: '이름을 입력하세요' }]}>
              <Input placeholder="기본 승인 워크플로우" />
            </Form.Item>

            <Form.Item name="is_active" label="활성화" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Text type="secondary" className="mb-4 block">
              워크플로우 단계 상세 설정은 Phase 1-B에서 지원됩니다.
              현재는 기본 1단계 승인(CD 승인)이 적용됩니다.
            </Text>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>저장</Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </div>
  );
}
