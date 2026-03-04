export type MediaType = 'IMAGE' | 'VIDEO' | 'AUDIO' | 'DOCUMENT';

export interface MediaAsset {
  id: string;
  organization_id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  media_type: MediaType;
  object_key: string;
  file_size: number;
  duration: number | null;
  width: number | null;
  height: number | null;
  tags: string[];
  metadata: Record<string, unknown> | null;
  folder_id: string | null;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface MediaAssetListItem {
  id: string;
  organization_id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  media_type: MediaType;
  object_key: string;
  file_size: number;
  duration: number | null;
  width: number | null;
  height: number | null;
  tags: string[];
  folder_id: string | null;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface MediaFolder {
  id: string;
  organization_id: string;
  name: string;
  parent_id: string | null;
  created_at: string;
}

export interface MediaListParams {
  page?: number;
  limit?: number;
  media_type?: MediaType;
  folder_id?: string;
  search?: string;
  tags?: string[];
}

export interface MediaUploadData {
  filename: string;
  original_filename: string;
  content_type: string;
  object_key: string;
  file_size: number;
  duration?: number;
  width?: number;
  height?: number;
  tags?: string[];
  metadata?: Record<string, unknown>;
  folder_id?: string;
}

export interface MediaUpdateData {
  filename?: string;
  tags?: string[];
  folder_id?: string | null;
}

export interface MediaFolderCreateData {
  name: string;
  parent_id?: string;
}

export interface PresignedUploadData {
  filename: string;
  content_type: string;
  file_size: number;
}

export interface PresignedUploadResult {
  upload_url: string;
  object_key: string;
  public_url: string;
  content_type: string;
  filename: string;
}
