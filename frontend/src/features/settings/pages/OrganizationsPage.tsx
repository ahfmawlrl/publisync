import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import { getOrgStatusConfig, ORG_STATUS_CONFIG, PLAN_OPTIONS } from '@/shared/constants/userStatus';

const { Title } = Typography;

interface OrgRecord {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: string;
  created_at: string;
}

export default function OrganizationsPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingOrg, setEditingOrg] = useState<OrgRecord | null>(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  const { data, isLoading } = useQuery({
    queryKey: ['organizations', { page }],
    queryFn: async () => {
      const res = await apiClient.get<PaginatedResponse<OrgRecord>>('/organizations', {
        params: { page, limit: 20 },
      });
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (values: { name: string; slug: string; plan: string }) => {
      const res = await apiClient.post<ApiResponse<OrgRecord>>('/organizations', values);
      return res.data.data;
    },
    onSuccess: () => {
      message.success('위탁기관이 생성되었습니다');
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
      setCreateOpen(false);
      form.resetFields();
    },
    onError: () => message.error('위탁기관 생성에 실패했습니다'),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...body }: { id: string; name?: string; plan?: string; status?: string }) => {
      const res = await apiClient.put<ApiResponse<OrgRecord>>(`/organizations/${id}`, body);
      return res.data.data;
    },
    onSuccess: () => {
      message.success('위탁기관 정보가 수정되었습니다');
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
      setEditOpen(false);
      setEditingOrg(null);
    },
    onError: () => message.error('위탁기관 수정에 실패했습니다'),
  });

  const deleteMutation = useMutation({
    mutationFn: async (orgId: string) => {
      await apiClient.delete(`/organizations/${orgId}`);
    },
    onSuccess: () => {
      message.success('위탁기관이 삭제되었습니다');
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
    },
    onError: () => message.error('위탁기관 삭제에 실패했습니다'),
  });

  const handleEdit = (org: OrgRecord) => {
    setEditingOrg(org);
    editForm.setFieldsValue({ name: org.name, plan: org.plan, status: org.status });
    setEditOpen(true);
  };

  const columns: ColumnsType<OrgRecord> = [
    { title: '기관명', dataIndex: 'name', key: 'name' },
    { title: '슬러그', dataIndex: 'slug', key: 'slug' },
    {
      title: '플랜',
      dataIndex: 'plan',
      key: 'plan',
      render: (plan: string) => {
        const opt = PLAN_OPTIONS.find((p) => p.value === plan);
        return <Tag>{opt?.label || plan}</Tag>;
      },
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const cfg = getOrgStatusConfig(status);
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '생성일',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => new Date(v).toLocaleDateString('ko-KR'),
    },
    {
      title: '관리',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm
            title="위탁기관을 삭제하시겠습니까?"
            description="이 작업은 되돌릴 수 없습니다."
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="삭제"
            cancelText="취소"
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">위탁기관 관리</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          기관 추가
        </Button>
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

      {/* 기관 생성 모달 */}
      <Modal
        title="위탁기관 추가"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending}
        okText="추가"
        cancelText="취소"
      >
        <Form form={form} layout="vertical" onFinish={createMutation.mutate}>
          <Form.Item name="name" label="기관명" rules={[{ required: true, message: '기관명을 입력하세요' }]}>
            <Input placeholder="예: 서울특별시" />
          </Form.Item>
          <Form.Item
            name="slug"
            label="슬러그"
            rules={[
              { required: true, message: '슬러그를 입력하세요' },
              { pattern: /^[a-z0-9-]+$/, message: '소문자, 숫자, 하이픈만 사용 가능합니다' },
            ]}
          >
            <Input placeholder="예: seoul-city" />
          </Form.Item>
          <Form.Item name="plan" label="플랜" rules={[{ required: true, message: '플랜을 선택하세요' }]}>
            <Select options={PLAN_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 기관 수정 모달 */}
      <Modal
        title="위탁기관 수정"
        open={editOpen}
        onCancel={() => { setEditOpen(false); setEditingOrg(null); }}
        onOk={() => editForm.submit()}
        confirmLoading={updateMutation.isPending}
        okText="저장"
        cancelText="취소"
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={(values) => {
            if (editingOrg) updateMutation.mutate({ id: editingOrg.id, ...values });
          }}
        >
          <Form.Item name="name" label="기관명" rules={[{ required: true, message: '기관명을 입력하세요' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="plan" label="플랜" rules={[{ required: true, message: '플랜을 선택하세요' }]}>
            <Select options={PLAN_OPTIONS} />
          </Form.Item>
          <Form.Item name="status" label="상태">
            <Select
              options={Object.entries(ORG_STATUS_CONFIG).map(([value, { text }]) => ({ value, label: text }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
