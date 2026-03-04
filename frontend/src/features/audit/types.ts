export interface AuditLogRecord {
  id: string;
  organization_id: string;
  actor_id: string | null;
  actor_role: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  request_id: string | null;
  created_at: string;
}

export interface AuditLogFilters {
  page?: number;
  limit?: number;
  action?: string;
  resource_type?: string;
  actor_id?: string;
  start_date?: string;
  end_date?: string;
}

export interface AuditLogExportParams {
  format: 'csv' | 'pdf';
  start_date: string;
  end_date: string;
  actions?: string;
}
