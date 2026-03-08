import { DeleteOutlined, EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { App, Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Table, Tabs, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse, PaginatedResponse } from '@/shared/api/types';
import { useWorkspace } from '@/shared/hooks/useWorkspace';
import type { Role } from '@/shared/types';
import { getRoleConfig, ROLE_OPTIONS, ROLE_FILTER_OPTIONS } from '@/shared/constants/roles';
import { getUserStatusConfig, USER_STATUS_FILTER_OPTIONS, USER_STATUS_OPTIONS } from '@/shared/constants/userStatus';

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
    mutationFn: async ({ id, ...body }: { id: string; role?: string; name?: string; status?: string }) => {
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
    editForm.setFieldsValue({ name: user.name, role: user.role, status: user.status });
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
        <Tag color={getRoleConfig(role).color}>{getRoleConfig(role).label}</Tag>
      ),
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const s = getUserStatusConfig(status);
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
                      options={USER_STATUS_FILTER_OPTIONS}
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
              <Table
                size="small"
                pagination={false}
                rowKey="feature"
                dataSource={[
                  { feature: '콘텐츠 작성/수정', SA: '✅', AM: '✅', AO: '✅', CD: '—' },
                  { feature: '콘텐츠 게시 요청', SA: '✅', AM: '✅', AO: '✅', CD: '—' },
                  { feature: '승인/반려', SA: '✅', AM: '✅', AO: '—', CD: '✅' },
                  { feature: '댓글 관리', SA: '✅', AM: '✅', AO: '✅', CD: '조회' },
                  { feature: '채널 연동 관리', SA: '✅', AM: '✅', AO: '—', CD: '—' },
                  { feature: '대시보드 조회', SA: '✅', AM: '✅', AO: '✅', CD: '✅' },
                  { feature: '기관 비교 뷰', SA: '✅', AM: '✅', AO: '—', CD: '—' },
                  { feature: '성과 분석/리포트', SA: '✅', AM: '✅', AO: '조회', CD: '조회' },
                  { feature: '사용자 초대/관리', SA: '✅', AM: '✅', AO: '—', CD: '—' },
                  { feature: '워크플로우 설정', SA: '✅', AM: '✅', AO: '—', CD: '—' },
                  { feature: '알림 설정', SA: '✅', AM: '✅', AO: '✅', CD: '✅' },
                  { feature: '감사 로그 조회', SA: '✅', AM: '✅', AO: '—', CD: '—' },
                  { feature: '시스템 관리', SA: '✅', AM: '—', AO: '—', CD: '—' },
                ]}
                columns={[
                  { title: '기능', dataIndex: 'feature', key: 'feature', width: 200 },
                  { title: 'SA (시스템 관리자)', dataIndex: 'SA', key: 'SA', align: 'center', width: 140 },
                  { title: 'AM (수탁 관리자)', dataIndex: 'AM', key: 'AM', align: 'center', width: 140 },
                  { title: 'AO (수탁 실무자)', dataIndex: 'AO', key: 'AO', align: 'center', width: 140 },
                  { title: 'CD (위탁 담당자)', dataIndex: 'CD', key: 'CD', align: 'center', width: 140 },
                ]}
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
          <Form.Item name="status" label="상태">
            <Select options={USER_STATUS_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
