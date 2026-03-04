export interface ContentRecord {
  id: string;
  organization_id: string;
  title: string;
  body: string | null;
  status: string;
  platforms: string[];
  channel_ids: string[];
  scheduled_at: string | null;
  author_id: string;
  platform_contents: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  ai_generated: boolean;
  media_urls: string[];
  created_at: string;
  updated_at: string;
}

export interface PublishResultRecord {
  id: string;
  content_id: string;
  channel_id: string;
  status: string;
  platform_post_id: string | null;
  platform_url: string | null;
  error_message: string | null;
  retry_count: number;
  views: number;
  likes: number;
  shares: number;
  comments_count: number;
  created_at: string;
}

export interface ContentCreateData {
  title: string;
  body?: string;
  platforms: string[];
  channel_ids: string[];
  scheduled_at?: string;
  platform_contents?: Record<string, unknown>;
  media_urls?: string[];
  ai_generated?: boolean;
  metadata?: Record<string, unknown>;
}

export interface ContentUpdateData {
  title?: string;
  body?: string;
  platforms?: string[];
  channel_ids?: string[];
  scheduled_at?: string | null;
  platform_contents?: Record<string, unknown>;
  media_urls?: string[];
  metadata?: Record<string, unknown>;
}
