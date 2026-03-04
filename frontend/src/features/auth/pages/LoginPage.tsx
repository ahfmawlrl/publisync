import { LockOutlined, MailOutlined } from '@ant-design/icons';
import { App, Button, Card, Checkbox, Form, Input, Typography } from 'antd';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router';

import { useLogin } from '../hooks/useLogin';

const { Title, Text } = Typography;

interface LoginFormData {
  email: string;
  password: string;
  remember_me: boolean;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const login = useLogin();
  const [form] = Form.useForm<LoginFormData>();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: LoginFormData) => {
    setLoading(true);
    try {
      await login.mutateAsync(values);
      message.success('로그인 성공');
      navigate('/');
    } catch (err: unknown) {
      const error = err as {
        response?: { status?: number; data?: { error?: { message?: string } } };
      };
      const status = error?.response?.status;
      const msg = error?.response?.data?.error?.message;

      if (status === 423) {
        message.error('계정이 잠겼습니다. 30분 후 다시 시도하세요.');
      } else if (status === 401) {
        message.error(msg || '이메일 또는 비밀번호가 올바르지 않습니다.');
      } else {
        message.error('로그인에 실패했습니다. 다시 시도하세요.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <Title level={3} className="!mb-1">
            PubliSync
          </Title>
          <Text type="secondary">공공기관 소셜 미디어 통합 관리</Text>
        </div>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ remember_me: false }}
          autoComplete="off"
        >
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '이메일을 입력하세요' },
              { type: 'email', message: '올바른 이메일 형식이 아닙니다' },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="이메일"
              size="large"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '비밀번호를 입력하세요' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="비밀번호"
              size="large"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item>
            <div className="flex items-center justify-between">
              <Form.Item name="remember_me" valuePropName="checked" noStyle>
                <Checkbox>로그인 유지</Checkbox>
              </Form.Item>
              <Link to="/reset-password">비밀번호 찾기</Link>
            </div>
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={loading}>
              로그인
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </main>
  );
}
