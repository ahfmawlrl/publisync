export interface ChannelRecord {
  id: string;
  organization_id: string;
  platform: string;
  platform_account_id: string;
  name: string;
  status: string;
  token_expires_at: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ChannelHistoryRecord {
  id: string;
  channel_id: string;
  event_type: string;
  details: Record<string, unknown> | null;
  actor_id: string | null;
  actor_name: string | null;
  created_at: string;
}

export interface ConnectInitiateResponse {
  auth_url: string;
  state: string;
}

export interface ApiStatusRecord {
  platform: string;
  requests_used: number;
  requests_limit: number;
  window: string;
  percentage_used: number;
}
