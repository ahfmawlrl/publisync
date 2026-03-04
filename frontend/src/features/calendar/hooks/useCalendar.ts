import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import apiClient from '@/shared/api/client';
import type { ApiResponse } from '@/shared/api/types';
import type { CalendarEvent, CalendarEventParams, HolidayCreateData, RescheduleRequest } from '../types';

// -- GET /calendar/events ------------------------------------------------

export function useCalendarEvents(params: CalendarEventParams) {
  return useQuery({
    queryKey: ['calendar-events', params],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<CalendarEvent[]>>('/calendar/events', {
        params,
      });
      return res.data.data;
    },
    enabled: !!params.start_date && !!params.end_date,
  });
}

// -- PATCH /calendar/events/:id/reschedule --------------------------------

export function useRescheduleEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: RescheduleRequest }) => {
      const res = await apiClient.patch<ApiResponse<CalendarEvent>>(
        `/calendar/events/${id}/reschedule`,
        data,
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar-events'] });
    },
  });
}

// -- GET /calendar/holidays -----------------------------------------------

export function useHolidays(year: number) {
  return useQuery({
    queryKey: ['calendar-holidays', year],
    queryFn: async () => {
      const res = await apiClient.get<ApiResponse<CalendarEvent[]>>('/calendar/holidays', {
        params: { year },
      });
      return res.data.data;
    },
  });
}

// -- PUT /calendar/holidays -----------------------------------------------

export function useUpdateHolidays() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (holidays: HolidayCreateData[]) => {
      const res = await apiClient.put<ApiResponse<CalendarEvent[]>>('/calendar/holidays', {
        holidays,
      });
      return res.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar-holidays'] });
      queryClient.invalidateQueries({ queryKey: ['calendar-events'] });
    },
  });
}
