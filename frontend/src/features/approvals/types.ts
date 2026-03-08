export interface ApprovalRequestRecord {
  id: string;
  content_id: string;
  content_title?: string;
  platforms?: string[];
  organization_id: string;
  workflow_id: string | null;
  current_step: number;
  status: string;
  requested_by: string;
  is_urgent: boolean;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalHistoryRecord {
  id: string;
  request_id: string;
  step: number;
  action: string;
  reviewer_id: string | null;
  comment: string | null;
  created_at: string;
}

export interface WorkflowRecord {
  id: string;
  organization_id: string;
  name: string;
  steps: Record<string, unknown>[] | null;
  is_active: boolean;
  created_at: string;
}
