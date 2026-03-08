import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Empty, Form, Input, List, Select, Space, Switch, Typography } from 'antd';
import { useEffect, useState } from 'react';

import { useUpdateWorkflow, useWorkflows } from '../hooks/useApprovals';
import type { WorkflowRecord } from '../types';

const { Title, Text } = Typography;

const ROLE_OPTIONS = [
  { value: 'CLIENT_DIRECTOR', label: '위탁기관 담당자 (CD)' },
  { value: 'AGENCY_MANAGER', label: '수탁업체 관리자 (AM)' },
];

interface WorkflowStep {
  order: number;
  approver_role: string;
  label: string;
}

export default function WorkflowSettingsPage() {
  const { message } = App.useApp();
  const { data: workflows, isLoading } = useWorkflows();
  const updateMutation = useUpdateWorkflow();
  const [form] = Form.useForm();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [steps, setSteps] = useState<WorkflowStep[]>([
    { order: 1, approver_role: 'CLIENT_DIRECTOR', label: 'CD 승인' },
  ]);

  // Auto-select the first workflow on load
  useEffect(() => {
    if (workflows && workflows.length > 0 && !selectedId) {
      selectWorkflow(workflows[0]);
    }
  }, [workflows]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectWorkflow = (wf: WorkflowRecord) => {
    setSelectedId(wf.id);
    form.setFieldsValue({ name: wf.name, is_active: wf.is_active });
    if (wf.steps && wf.steps.length > 0) {
      setSteps(
        wf.steps.map((s, i) => ({
          order: (s.order as number) ?? i + 1,
          approver_role: (s.approver_role as string) ?? 'CLIENT_DIRECTOR',
          label: (s.label as string) ?? `${i + 1}단계`,
        })),
      );
    } else {
      setSteps([{ order: 1, approver_role: 'CLIENT_DIRECTOR', label: 'CD 승인' }]);
    }
  };

  const handleSave = async (values: Record<string, unknown>) => {
    try {
      await updateMutation.mutateAsync({
        name: values.name as string,
        is_active: values.is_active as boolean,
        steps: steps.map((s, i) => ({ ...s, order: i + 1 })),
      });
      message.success('워크플로우가 저장되었습니다');
    } catch {
      message.error('워크플로우 저장에 실패했습니다');
    }
  };

  const addStep = () => {
    setSteps((prev) => [
      ...prev,
      { order: prev.length + 1, approver_role: 'CLIENT_DIRECTOR', label: `${prev.length + 1}단계 승인` },
    ]);
  };

  const removeStep = (index: number) => {
    if (steps.length <= 1) return;
    setSteps((prev) => prev.filter((_, i) => i !== index));
  };

  const updateStep = (index: number, field: keyof WorkflowStep, value: string) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? { ...s, [field]: value } : s)));
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
                <List.Item
                  className={`cursor-pointer rounded px-2 transition-colors hover:bg-gray-50 ${selectedId === wf.id ? 'bg-blue-50' : ''}`}
                  onClick={() => selectWorkflow(wf)}
                >
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

            {/* Workflow steps */}
            <div className="mb-4">
              <div className="mb-2 flex items-center justify-between">
                <Text strong>승인 단계</Text>
                <Button size="small" icon={<PlusOutlined />} onClick={addStep}>
                  단계 추가
                </Button>
              </div>

              <div className="space-y-2">
                {steps.map((step, index) => (
                  <div key={index} className="flex items-center gap-2 rounded border border-gray-200 p-2">
                    <Text className="w-8 text-center text-xs text-gray-400">{index + 1}</Text>
                    <Input
                      size="small"
                      placeholder="단계 이름"
                      value={step.label}
                      onChange={(e) => updateStep(index, 'label', e.target.value)}
                      style={{ flex: 1 }}
                    />
                    <Select
                      size="small"
                      value={step.approver_role}
                      onChange={(val) => updateStep(index, 'approver_role', val)}
                      options={ROLE_OPTIONS}
                      style={{ width: 200 }}
                    />
                    <Button
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      disabled={steps.length <= 1}
                      onClick={() => removeStep(index)}
                    />
                  </div>
                ))}
              </div>
              <Text type="secondary" className="mt-1 block text-xs">
                콘텐츠 게시 요청 시 위에서 아래 순서로 승인을 받습니다.
              </Text>
            </div>

            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>저장</Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </div>
  );
}
