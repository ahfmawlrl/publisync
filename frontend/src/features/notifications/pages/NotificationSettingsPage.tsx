import { MailOutlined, SendOutlined } from '@ant-design/icons';
import { App, Button, Card, Input, Switch, Table, Tabs, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useCallback, useEffect, useState } from 'react';

import {
  useNotificationSettings,
  useSendTelegramTest,
  useUpdateNotificationSettings,
} from '../hooks/useNotifications';
import type { NotificationChannelConfig } from '../types';

const { Title, Text } = Typography;

interface NotifTypeRow {
  key: string;
  label: string;
  description: string;
}

const NOTIFICATION_TYPES: NotifTypeRow[] = [
  { key: 'dangerous_comment', label: '위험 댓글 감지', description: '위험 수준의 댓글이 감지되면 알림' },
  { key: 'approval_request', label: '승인 요청', description: '내가 검수자일 때 승인 요청 알림' },
  { key: 'approval_result', label: '승인/반려 결과', description: '내가 요청한 콘텐츠의 승인/반려 결과' },
  { key: 'publish_complete', label: '게시 완료', description: '콘텐츠가 성공적으로 게시되면 알림' },
  { key: 'publish_failed', label: '게시 실패', description: '콘텐츠 게시에 실패하면 알림' },
  { key: 'token_expiring', label: '토큰 만료 임박', description: '채널 토큰 만료가 임박하면 알림' },
  { key: 'system', label: '시스템 공지', description: '시스템 점검, 업데이트 등의 공지' },
];

export default function NotificationSettingsPage() {
  const { message } = App.useApp();
  const { data: settings, isLoading } = useNotificationSettings();
  const updateMutation = useUpdateNotificationSettings();
  const telegramTestMutation = useSendTelegramTest();

  const [channels, setChannels] = useState<NotificationChannelConfig>({
    web: { enabled: true },
    email: { enabled: false },
    telegram: { enabled: false },
    webPush: { enabled: false },
  });
  const [telegramChatId, setTelegramChatId] = useState('');

  // Per-type toggle state: Record<notifTypeKey, boolean>
  const [typeToggles, setTypeToggles] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(NOTIFICATION_TYPES.map((t) => [t.key, true])),
  );

  useEffect(() => {
    if (settings) {
      setChannels(settings.channels);
      setTelegramChatId(settings.telegram_chat_id || '');
    }
  }, [settings]);

  const toggleType = useCallback((key: string, checked: boolean) => {
    setTypeToggles((prev) => ({ ...prev, [key]: checked }));
  }, []);

  const handleSave = async () => {
    try {
      await updateMutation.mutateAsync({
        channels,
        telegram_chat_id: telegramChatId || undefined,
      });
      message.success('알림 설정이 저장되었습니다');
    } catch {
      message.error('알림 설정 저장에 실패했습니다');
    }
  };

  const handleTelegramTest = async () => {
    if (!telegramChatId) {
      message.warning('텔레그램 Chat ID를 입력하세요');
      return;
    }
    try {
      const result = await telegramTestMutation.mutateAsync(telegramChatId);
      if (result.sent) {
        message.success('테스트 알림이 발송되었습니다');
      } else {
        message.warning(result.message || '발송에 실패했습니다');
      }
    } catch {
      message.error('테스트 알림 발송에 실패했습니다');
    }
  };

  const typeToggleColumn = {
    title: '수신',
    key: 'enabled',
    width: 80,
    align: 'center' as const,
    render: (_: unknown, record: NotifTypeRow) => (
      <Switch
        checked={typeToggles[record.key] ?? true}
        onChange={(checked) => toggleType(record.key, checked)}
        size="small"
      />
    ),
  };

  const webColumns: ColumnsType<NotifTypeRow> = [
    { title: '알림 유형', dataIndex: 'label', key: 'label' },
    {
      title: '설명',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => <Text type="secondary">{desc}</Text>,
    },
    typeToggleColumn,
  ];

  const webPushColumns: ColumnsType<NotifTypeRow> = [
    { title: '알림 유형', dataIndex: 'label', key: 'label' },
    typeToggleColumn,
  ];

  const tabItems = [
    {
      key: 'web',
      label: '웹 알림',
      children: (
        <Card loading={isLoading}>
          <div className="mb-3 flex items-center justify-between">
            <Text strong>웹 알림 수신 설정</Text>
            <Switch
              checked={channels.web.enabled}
              onChange={(checked) =>
                setChannels((prev) => ({ ...prev, web: { enabled: checked } }))
              }
            />
          </div>
          <Table
            columns={webColumns}
            dataSource={NOTIFICATION_TYPES}
            rowKey="key"
            pagination={false}
            size="small"
          />
        </Card>
      ),
    },
    {
      key: 'email',
      label: '이메일',
      children: (
        <Card loading={isLoading}>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <Text strong>이메일 알림 수신</Text>
              <br />
              <Text type="secondary" className="text-xs">
                <MailOutlined className="mr-1" />
                등록된 이메일 주소로 알림을 수신합니다
              </Text>
            </div>
            <Switch
              checked={channels.email.enabled}
              onChange={(checked) =>
                setChannels((prev) => ({ ...prev, email: { enabled: checked } }))
              }
            />
          </div>
          {channels.email.enabled && (
            <Table
              columns={webPushColumns}
              dataSource={NOTIFICATION_TYPES}
              rowKey="key"
              pagination={false}
              size="small"
            />
          )}
        </Card>
      ),
    },
    {
      key: 'telegram',
      label: '텔레그램',
      children: (
        <Card loading={isLoading}>
          <div className="mb-4 flex items-center justify-between">
            <Text strong>텔레그램 알림</Text>
            <Switch
              checked={channels.telegram.enabled}
              onChange={(checked) =>
                setChannels((prev) => ({ ...prev, telegram: { enabled: checked } }))
              }
            />
          </div>

          {channels.telegram.enabled && (
            <>
              <div className="mb-4">
                <Text type="secondary" className="mb-2 block">
                  봇 연결: @PubliSync_Bot
                  {telegramChatId ? (
                    <span className="ml-2 text-green-600">연결됨</span>
                  ) : (
                    <span className="ml-2 text-orange-500">미연결</span>
                  )}
                </Text>
                <div className="flex gap-2">
                  <Input
                    placeholder="Telegram Chat ID"
                    value={telegramChatId}
                    onChange={(e) => setTelegramChatId(e.target.value)}
                    style={{ maxWidth: 300 }}
                  />
                  <Button
                    icon={<SendOutlined />}
                    onClick={handleTelegramTest}
                    loading={telegramTestMutation.isPending}
                  >
                    테스트 알림 발송
                  </Button>
                </div>
              </div>

              <Table
                columns={webPushColumns}
                dataSource={NOTIFICATION_TYPES}
                rowKey="key"
                pagination={false}
                size="small"
              />
            </>
          )}
        </Card>
      ),
    },
    {
      key: 'webpush',
      label: '웹 푸시',
      children: (
        <Card loading={isLoading}>
          <div className="mb-4 flex items-center justify-between">
            <Text strong>웹 푸시 알림</Text>
            <Switch
              checked={channels.webPush.enabled}
              onChange={(checked) =>
                setChannels((prev) => ({ ...prev, webPush: { enabled: checked } }))
              }
            />
          </div>

          {channels.webPush.enabled && (
            <>
              <Text type="secondary" className="mb-4 block">
                브라우저 알림 상태: {typeof Notification !== 'undefined' && Notification.permission === 'granted'
                  ? '알림 허용됨'
                  : '알림 미허용'}
              </Text>

              <Table
                columns={webPushColumns}
                dataSource={NOTIFICATION_TYPES}
                rowKey="key"
                pagination={false}
                size="small"
              />
            </>
          )}
        </Card>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Title level={4} className="!mb-0">
          알림 설정
        </Title>
        <Button type="primary" onClick={handleSave} loading={updateMutation.isPending}>
          저장
        </Button>
      </div>

      <Tabs items={tabItems} />
    </div>
  );
}
