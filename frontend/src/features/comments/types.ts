export interface CommentRecord {
  id: string;
  organization_id: string;
  content_id: string | null;
  channel_id: string;
  platform: string;
  external_id: string;
  text: string;
  author_name: string;
  author_profile_url: string | null;
  parent_comment_id: string | null;
  sentiment: string | null;
  sentiment_confidence: number | null;
  dangerous_level: string | null;
  keywords: string[] | null;
  status: string;
  reply_text: string | null;
  reply_draft: string | null;
  replied_at: string | null;
  hidden_reason: string | null;
  delete_reason: string | null;
  processed_by: string | null;
  platform_created_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReplyTemplateRecord {
  id: string;
  organization_id: string;
  category: string;
  name: string;
  content: string;
  variables: string[] | null;
  usage_count: number;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ReplyTemplateCreateData {
  category: string;
  name: string;
  content: string;
  variables?: string[];
}

export interface ReplyTemplateUpdateData {
  category?: string;
  name?: string;
  content?: string;
  variables?: string[];
  is_active?: boolean;
}
