// ── Variant types (v2.0) ────────────────────────────

export interface VariantMediaRecord {
  id: string;
  media_asset_id: string;
  role: string;
  sort_order: number;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface VariantRecord {
  id: string;
  content_id: string;
  organization_id: string;
  platform: string;
  channel_id: string | null;
  title: string | null;
  body: string | null;
  hashtags: string[];
  metadata: Record<string, unknown> | null;
  sort_order: number;
  media: VariantMediaRecord[];
  created_at: string;
  updated_at: string;
}

export interface VariantCreateData {
  platform: string;
  channel_id?: string;
  title?: string;
  body?: string;
  hashtags?: string[];
  metadata?: Record<string, unknown>;
  sort_order?: number;
}

export interface VariantUpdateData {
  title?: string;
  body?: string;
  hashtags?: string[];
  metadata?: Record<string, unknown>;
  sort_order?: number;
}

export interface VariantMediaAttachData {
  media_asset_id: string;
  role?: string;
  sort_order?: number;
  metadata?: Record<string, unknown>;
}

// ── Content types ───────────────────────────────────

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
  author_name: string | null;
  platform_contents: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  hashtags: string[];
  ai_generated: boolean;
  media_urls: string[];
  source_media_id: string | null;
  variants: VariantRecord[];
  created_at: string;
  updated_at: string;
}

export interface PublishResultRecord {
  id: string;
  content_id: string;
  variant_id: string | null;
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
  hashtags?: string[];
  ai_generated?: boolean;
  metadata?: Record<string, unknown>;
  source_media_id?: string;
  variants?: VariantCreateData[];
  uniform_publish?: boolean;
}

export interface ContentUpdateData {
  title?: string;
  body?: string;
  platforms?: string[];
  channel_ids?: string[];
  scheduled_at?: string | null;
  platform_contents?: Record<string, unknown>;
  media_urls?: string[];
  hashtags?: string[];
  metadata?: Record<string, unknown>;
  source_media_id?: string;
}
