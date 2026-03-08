import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { App, Button, Card, Form, Input, Result, Spin, Typography } from 'antd';
import { Link, useNavigate, useSearchParams } from 'react-router';

import { useInviteAccept, useInviteVerify } from '../hooks/useInvite';

import { getRoleLabel } from '@/shared/constants/roles';

const { Title, Text } = Typography;

export default function InvitePage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const { message } = App.useApp();

  const { data: invite, isLoading, isError } = useInviteVerify(token);
  const acceptMutation = useInviteAccept();

  if (!token) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <Result status="error" title="잘못된 초대 링크" extra={<Link to="/login">로그인</Link>} />
      </main>
    );
  }

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Spin size="large" />
      </main>
    );
  }

  if (isError || !invite) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <Result
          status="warning"
          title="초대가 만료되었거나 유효하지 않습니다"
          extra={<Link to="/login">로그인</Link>}
        />
      </main>
    );
  }

  const handleSubmit = async (values: { name: string; password: string }) => {
    try {
      await acceptMutation.mutateAsync({ token, name: values.name, password: values.password });
      message.success('가입이 완료되었습니다');
      navigate('/');
    } catch {
      message.error('가입에 실패했습니다. 다시 시도하세요.');
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <Title level={3} className="!mb-1">
            초대 수락
          </Title>
          <Text type="secondary">
            <strong>{invite.organization_name}</strong>에서 초대했습니다
          </Text>
          <br />
          <Text type="secondary">
            {invite.email} / {getRoleLabel(invite.role)}
          </Text>
        </div>

        <Form layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" rules={[{ required: true, message: '이름을 입력하세요' }]}>
            <Input prefix={<UserOutlined />} placeholder="이름" size="large" />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '비밀번호를 입력하세요' },
              { min: 8, message: '8자 이상 입력하세요' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="비밀번호" size="large" />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            dependencies={['password']}
            rules={[
              { required: true, message: '비밀번호를 다시 입력하세요' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('비밀번호가 일치하지 않습니다'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="비밀번호 확인" size="large" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={acceptMutation.isPending}>
              가입 및 시작하기
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </main>
  );
}
