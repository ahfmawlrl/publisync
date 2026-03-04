export interface Report {
  id: string;
  organization_id: string;
  title: string;
  period: 'WEEKLY' | 'MONTHLY' | 'QUARTERLY';
  period_start: string;
  period_end: string;
  status: 'GENERATING' | 'DRAFT' | 'FINALIZED';
  content: Record<string, ReportSection>;
  pdf_url: string | null;
  generated_by: string | null;
  created_by: string;
  finalized_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportSection {
  type: 'AI_TEXT' | 'CHART_DATA' | 'TABLE_DATA';
  content?: string;
  data?: unknown;
}

export interface ReportListItem {
  id: string;
  title: string;
  period: string;
  period_start: string;
  period_end: string;
  status: string;
  generated_by: string | null;
  created_at: string;
  finalized_at: string | null;
}

export interface GenerateReportRequest {
  period: string;
  period_start: string;
  period_end: string;
  include_sections?: string[];
}
