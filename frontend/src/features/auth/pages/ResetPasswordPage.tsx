import { MailOutlined } from '@ant-design/icons';
import { App, Button, Card, Form, Input, Result, Typography } from 'antd';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { usePasswordReset, usePasswordResetRequest } from '../hooks/usePasswordReset';

const { Title, Text } = Typography;

/** Renders request form or reset form depending on ?token= query param. */
export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  return token ? <ResetForm token={token} /> : <RequestForm />;
}

// ── Step 1: Request reset email ─────────────────────────

function RequestForm() {
  const { message } = App.useApp();
  const mutation = usePasswordResetRequest();
  const [sent, setSent] = useState(false);

  const handleSubmit = async (values: { email: string }) => {
    try {
      await mutation.mutateAsync(values);
      setSent(true);
    } catch {
      message.error('요청 처리에 실패했습니다. 다시 시도하세요.');
    }
  };

  if (sent) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <Card className="w-full max-w-sm">
          <Result
            status="success"
            title="이메일을 확인하세요"
            subTitle="비밀번호 재설정 링크가 이메일로 전송되었습니다."
            extra={<Link to="/login">로그인으로 돌아가기</Link>}
          />
        </Card>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <Title level={3} className="!mb-1">
            비밀번호 찾기
          </Title>
          <Text type="secondary">가입한 이메일을 입력하세요</Text>
        </div>

        <Form layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '이메일을 입력하세요' },
              { type: 'email', message: '올바른 이메일 형식이 아닙니다' },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder="이메일" size="large" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              loading={mutation.isPending}
            >
              재설정 링크 전송
            </Button>
          </Form.Item>

          <div className="text-center">
            <Link to="/login">로그인으로 돌아가기</Link>
          </div>
        </Form>
      </Card>
    </main>
  );
}

// ── Step 2: Reset with token ────────────────────────────

function ResetForm({ token }: { token: string }) {
  const { message } = App.useApp();
  const mutation = usePasswordReset();
  const [done, setDone] = useState(false);

  const handleSubmit = async (values: { new_password: string }) => {
    try {
      await mutation.mutateAsync({ token, new_password: values.new_password });
      setDone(true);
    } catch {
      message.error('토큰이 만료되었거나 유효하지 않습니다.');
    }
  };

  if (done) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <Card className="w-full max-w-sm">
          <Result
            status="success"
            title="비밀번호가 변경되었습니다"
            subTitle="새 비밀번호로 로그인하세요."
            extra={<Link to="/login">로그인</Link>}
          />
        </Card>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <Title level={3} className="!mb-1">
            새 비밀번호 설정
          </Title>
        </div>

        <Form layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="new_password"
            rules={[
              { required: true, message: '새 비밀번호를 입력하세요' },
              { min: 8, message: '8자 이상 입력하세요' },
            ]}
          >
            <Input.Password placeholder="새 비밀번호" size="large" />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '비밀번호를 다시 입력하세요' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
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
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              loading={mutation.isPending}
            >
              비밀번호 변경
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </main>
  );
}
