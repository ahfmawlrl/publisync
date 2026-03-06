import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState } from 'react';

import {
  useCreateReplyTemplate,
  useDeleteReplyTemplate,
  useReplyTemplates,
  useUpdateReplyTemplate,
} from '../hooks/useComments';
import type { ReplyTemplateRecord } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const CATEGORY_OPTIONS = [
  { value: '민원·불만', label: '민원·불만' },
  { value: '정책 문의', label: '정책 문의' },
  { value: '칭찬·감사', label: '칭찬·감사' },
  { value: '행사·일정', label: '행사·일정' },
  { value: '기타', label: '기타' },
];

const CATEGORY_COLORS: Record<string, string> = {
  '민원·불만': 'red',
  '정책 문의': 'blue',
  '칭찬·감사': 'green',
  '행사·일정': 'orange',
  기타: 'default',
};

const TEMPLATE_VARIABLES = ['{기관명}', '{연락처}', '{담당부서}'];

export default function ReplyTemplatesPage() {
  const { message } = App.useApp();
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ReplyTemplateRecord | null>(null);
  const [form] = Form.useForm();

  const { data: templates, isLoading } = useReplyTemplates(category);
  const createMutation = useCreateReplyTemplate();
  const updateMutation = useUpdateReplyTemplate();
  const deleteMutation = useDeleteReplyTemplate();

  const filteredData = (templates || []).filter(
    (t) => !search || t.name.includes(search) || t.content.includes(search),
  );

  const openCreate = () => {
    setEditingTemplate(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalOpen(true);
  };

  const openEdit = (record: ReplyTemplateRecord) => {
    setEditingTemplate(record);
    form.setFieldsValue({
      name: record.name,
      category: record.category,
      content: record.content,
      is_active: record.is_active,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (values: {
    name: string;
    category: string;
    content: string;
    is_active: boolean;
  }) => {
    try {
      if (editingTemplate) {
        await updateMutation.mutateAsync({
          id: editingTemplate.id,
          data: {
            name: values.name,
            category: values.category,
            content: values.content,
            is_active: values.is_active,
          },
        });
        message.success('템플릿이 수정되었습니다');
      } else {
        await createMutation.mutateAsync({
          name: values.name,
          category: values.category,
          content: values.content,
        });
        message.success('템플릿이 생성되었습니다');
      }
      setModalOpen(false);
      setEditingTemplate(null);
      form.resetFields();
    } catch {
      message.error(editingTemplate ? '템플릿 수정에 실패했습니다' : '템플릿 생성에 실패했습니다');
    }
  };

  const columns: ColumnsType<ReplyTemplateRecord> = [
    {
      title: '카테고리',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (cat: string) => (
        <Tag color={CATEGORY_COLORS[cat] || 'default'}>{cat}</Tag>
      ),
    },
    {
      title: '템플릿명',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '사용 횟수',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 100,
      align: 'center',
    },
    {
      title: '상태',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>{active ? '활성' : '비활성'}</Tag>
      ),
    },
    {
      title: '관리',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(record)}
          />
          <Popconfirm
            title="템플릿을 삭제하시겠습니까?"
            onConfirm={() => {
              deleteMutation.mutate(record.id, {
                onSuccess: () => message.success('템플릿이 삭제되었습니다'),
                onError: () => message.error('템플릿 삭제에 실패했습니다'),
              });
            }}
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
          답글 템플릿 관리
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          새 템플릿
        </Button>
      </div>

      <div className="mb-4 flex gap-2">
        <Select
          allowClear
          placeholder="카테고리"
          options={CATEGORY_OPTIONS}
          value={category}
          onChange={setCategory}
          style={{ width: 160 }}
        />
        <Input.Search
          placeholder="검색..."
          allowClear
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 240 }}
        />
      </div>

      <Table
        columns={columns}
        dataSource={filteredData}
        rowKey="id"
        loading={isLoading}
        pagination={{ pageSize: 20, showTotal: (total) => `총 ${total}건` }}
      />

      <Modal
        title={editingTemplate ? '템플릿 수정' : '새 템플릿'}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setEditingTemplate(null);
        }}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        okText={editingTemplate ? '저장' : '생성'}
        cancelText="취소"
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="템플릿명"
            rules={[{ required: true, message: '템플릿명을 입력하세요' }]}
          >
            <Input placeholder="예: 민원 기본 안내" />
          </Form.Item>

          <Form.Item
            name="category"
            label="카테고리"
            rules={[{ required: true, message: '카테고리를 선택하세요' }]}
          >
            <Select options={CATEGORY_OPTIONS} placeholder="카테고리 선택" />
          </Form.Item>

          <Form.Item
            name="content"
            label="내용"
            rules={[{ required: true, message: '내용을 입력하세요' }]}
          >
            <TextArea rows={5} placeholder="답글 내용을 입력하세요..." />
          </Form.Item>

          <Text type="secondary" className="mb-4 block text-xs">
            사용 가능한 변수: {TEMPLATE_VARIABLES.join(', ')}
          </Text>

          {editingTemplate && (
            <Form.Item name="is_active" label="활성 상태" valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
