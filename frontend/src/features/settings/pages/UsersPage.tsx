import { DeleteOutlined, EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { App, Button, Card, Form, Input, Modal, Popconfirm, Result, Select, Space, Table, Tabs, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import { useWorkspace } from '@/shared/hooks/useWorkspace';
import type { Role } from '@/shared/types';

const { Title } = Typography;

interface UserRecord {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  last_login_at: string | null;
  created_at: string;
}

const ROLE_COLORS: Record<string, string> = {
  SYSTEM_ADMIN: 'red',
  AGENCY_MANAGER: 'blue',
  AGENCY_OPERATOR: 'green',
  CLIENT_DIRECTOR: 'orange',
};

const ROLE_LABELS: Record<string, string> = {
  SYSTEM_ADMIN: '시스템 관리자',
  AGENCY_MANAGER: '수탁업체 관리자',
  AGENCY_OPERATOR: '수탁업체 실무자',
  CLIENT_DIRECTOR: '위탁기관 담당자',
};

const ROLE_OPTIONS = [
  { value: 'AGENCY_MANAGER', label: '수탁업체 관리자' },
  { value: 'AGENCY_OPERATOR', label: '수탁업체 실무자' },
  { value: 'CLIENT_DIRECTOR', label: '위탁기관 담당자' },
];

const ROLE_FILTER_OPTIONS = [
  { value: '', label: '전체 역할' },
  { value: 'SYSTEM_ADMIN', label: '시스템 관리자' },
  { value: 'AGENCY_MANAGER', label: '수탁업체 관리자' },
  { value: 'AGENCY_OPERATOR', label: '수탁업체 실무자' },
  { value: 'CLIENT_DIRECTOR', label: '위탁기관 담당자' },
];

const STATUS_LABELS: Record<string, { color: string; text: string }> = {
  ACTIVE: { color: 'green', text: '활성' },
  INACTIVE: { color: 'default', text: '비활성' },
  LOCKED: { color: 'red', text: '잠금' },
  WITHDRAWN: { color: 'gray', text: '탈퇴' },
};

const STATUS_FILTER_OPTIONS = [
  { value: '', label: '전체 상태' },
  { value: 'ACTIVE', label: '활성' },
  { value: 'INACTIVE', label: '비활성' },
  { value: 'LOCKED', label: '잠금' },
  { value: 'WITHDRAWN', label: '탈퇴' },
];

export default function UsersPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const { workspaces } = useWorkspace();
  const [page, setPage] = useState(1);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // Search & filter state
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['users', { page, search: searchText, role: roleFilter, status: statusFilter }],
    queryFn: async () => {
      const params: Record<string, unknown> = { page, limit: 20 };
      if (searchText) params.search = searchText;
      if (roleFilter) params.role = roleFilter;
      if (statusFilter) params.status = statusFilter;
      const res = await apiClient.get<PaginatedResponse<UserRecord>>('/users', { params });
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (values: { email: string; name: string; role: Role; organization_id: string }) => {
      const res = await apiClient.post<ApiResponse<UserRecord>>('/users', values);
      return res.data.data;
    },
    onSuccess: () => {
      message.success('사용자가 생성되었습니다');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setInviteOpen(false);
      form.resetFields();
    },
    onError: () => {
      message.error('사용자 생성에 실패했습니다');
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...body }: { id: string; role?: string; name?: string }) => {
      const res = await apiClient.put<ApiResponse<UserRecord>>(`/users/${id}`, body);
      return res.data.data;
    },
    onSuccess: () => {
      message.success('사용자 정보가 수정되었습니다');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setEditOpen(false);
      setEditingUser(null);
    },
    onError: () => {
      message.error('사용자 수정에 실패했습니다');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (userId: string) => {
      await apiClient.delete(`/users/${userId}`);
    },
    onSuccess: () => {
      message.success('사용자가 삭제되었습니다');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => {
      message.error('사용자 삭제에 실패했습니다');
    },
  });

  const handleEdit = (user: UserRecord) => {
    setEditingUser(user);
    editForm.setFieldsValue({ name: user.name, role: user.role });
    setEditOpen(true);
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
    setPage(1);
  };

  const handleRoleFilter = (value: string) => {
    setRoleFilter(value);
    setPage(1);
  };

  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    setPage(1);
  };

  const columns: ColumnsType<UserRecord> = [
    { title: '이름', dataIndex: 'name', key: 'name' },
    { title: '이메일', dataIndex: 'email', key: 'email' },
    {
      title: '역할',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Tag color={ROLE_COLORS[role]}>{ROLE_LABELS[role] || role}</Tag>
      ),
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const s = STATUS_LABELS[status] || { color: 'default', text: status };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: '최근 로그인',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (v: string | null) => (v ? new Date(v).toLocaleDateString('ko-KR') : '-'),
    },
    {
      title: '관리',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm
            title="사용자를 삭제하시겠습니까?"
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
        <Title level={4} className="!mb-0">
          사용자 관리
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setInviteOpen(true)}>
          사용자 추가
        </Button>
      </div>

      <Tabs
        defaultActiveKey="users"
        items={[
          {
            key: 'users',
            label: '사용자 목록',
            children: (
              <>
                {/* Search & Filter Bar */}
                <Card size="small" className="mb-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Input.Search
                      placeholder="이름 또는 이메일 검색"
                      allowClear
                      prefix={<SearchOutlined />}
                      onSearch={handleSearch}
                      style={{ width: 280 }}
                    />
                    <Select
                      value={roleFilter}
                      onChange={handleRoleFilter}
                      options={ROLE_FILTER_OPTIONS}
                      style={{ width: 160 }}
                    />
                    <Select
                      value={statusFilter}
                      onChange={handleStatusFilter}
                      options={STATUS_FILTER_OPTIONS}
                      style={{ width: 140 }}
                    />
                  </div>
                </Card>

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
                    showTotal: (total) => `총 ${total}명`,
                  }}
                />
              </>
            ),
          },
          {
            key: 'roles',
            label: '역할 관리',
            children: (
              <Result
                status="info"
                title="역할 관리"
                subTitle="Phase 1-B에서 지원됩니다"
              />
            ),
          },
        ]}
      />

      {/* 사용자 추가 모달 */}
      <Modal
        title="사용자 추가"
        open={inviteOpen}
        onCancel={() => setInviteOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending}
        okText="추가"
        cancelText="취소"
      >
        <Form form={form} layout="vertical" onFinish={createMutation.mutate}>
          <Form.Item name="name" label="이름" rules={[{ required: true, message: '이름을 입력하세요' }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="email"
            label="이메일"
            rules={[
              { required: true, message: '이메일을 입력하세요' },
              { type: 'email', message: '올바른 이메일 형식이 아닙니다' },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="role" label="역할" rules={[{ required: true, message: '역할을 선택하세요' }]}>
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
          <Form.Item
            name="organization_id"
            label="소속 기관"
            rules={[{ required: true, message: '기관을 선택하세요' }]}
          >
            <Select
              placeholder="기관 선택"
              options={workspaces.map((w) => ({ value: w.id, label: w.name }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 역할 변경 모달 */}
      <Modal
        title="사용자 수정"
        open={editOpen}
        onCancel={() => { setEditOpen(false); setEditingUser(null); }}
        onOk={() => editForm.submit()}
        confirmLoading={updateMutation.isPending}
        okText="저장"
        cancelText="취소"
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={(values) => {
            if (editingUser) {
              updateMutation.mutate({ id: editingUser.id, ...values });
            }
          }}
        >
          <Form.Item name="name" label="이름" rules={[{ required: true, message: '이름을 입력하세요' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="역할" rules={[{ required: true, message: '역할을 선택하세요' }]}>
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
