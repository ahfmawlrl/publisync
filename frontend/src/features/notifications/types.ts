export interface NotificationRecord {
  id: string;
  organization_id: string;
  user_id: string;
  type: NotificationType;
  channel: string;
  title: string;
  message: string;
  payload: Record<string, unknown> | null;
  is_read: boolean;
  read_at: string | null;
  action_url: string | null;
  created_at: string;
}

export type NotificationType =
  | 'PUBLISH_COMPLETE'
  | 'PUBLISH_FAILED'
  | 'APPROVAL_REQUEST'
  | 'APPROVAL_RESULT'
  | 'DANGEROUS_COMMENT'
  | 'COMMENT_NEW'
  | 'TOKEN_EXPIRING'
  | 'SYSTEM';

export interface NotificationSettingRecord {
  id: string | null;
  organization_id: string;
  user_id: string;
  channels: NotificationChannelConfig;
  push_subscription: Record<string, unknown> | null;
  telegram_chat_id: string | null;
}

export interface NotificationChannelConfig {
  web: { enabled: boolean };
  email: { enabled: boolean };
  telegram: { enabled: boolean };
  webPush: { enabled: boolean };
}

export interface NotificationSettingUpdateData {
  channels?: NotificationChannelConfig;
  telegram_chat_id?: string;
}

export interface UnreadCountData {
  count: number;
}
