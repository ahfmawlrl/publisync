export interface CalendarEvent {
  id: string;
  organization_id: string;
  content_id: string | null;
  event_type: 'SCHEDULED_POST' | 'HOLIDAY' | 'ANNIVERSARY' | 'CUSTOM';
  title: string;
  description: string | null;
  event_date: string;
  scheduled_at: string | null;
  platform: string | null;
  status: string;
  is_holiday: boolean;
  is_recurring: boolean;
  color: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarEventParams {
  start_date: string;
  end_date: string;
  event_type?: string;
}

export interface RescheduleRequest {
  event_date: string;
  scheduled_at?: string;
}

export interface HolidayCreateData {
  event_type?: string;
  title: string;
  description?: string;
  event_date: string;
  scheduled_at?: string;
  platform?: string;
  is_holiday?: boolean;
  is_recurring?: boolean;
  color?: string;
}
