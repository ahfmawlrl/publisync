import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { EventClickArg, EventDropArg, EventInput } from '@fullcalendar/core';
import type { DateClickArg } from '@fullcalendar/interaction';
import { CalendarIcon, Plus, Trash2 } from 'lucide-react';
import {
  App,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';

import { getPlatformConfig } from '@/shared/constants/platform';
import {
  useCalendarEvents,
  useHolidays,
  useRescheduleEvent,
  useUpdateHolidays,
} from '../hooks/useCalendar';
import type { CalendarEvent, HolidayCreateData } from '../types';

const { Title, Text } = Typography;

const EVENT_TYPE_CONFIG: Record<string, { color: string; text: string }> = {
  SCHEDULED_POST: { color: 'blue', text: '예약 게시' },
  HOLIDAY: { color: 'red', text: '공휴일' },
  ANNIVERSARY: { color: 'gold', text: '기념일' },
  CUSTOM: { color: 'purple', text: '사용자 정의' },
};

/** FullCalendar background color by event type */
function getEventColor(eventType: string): string {
  switch (eventType) {
    case 'SCHEDULED_POST':
      return '#1677ff';
    case 'HOLIDAY':
      return '#ff4d4f';
    case 'ANNIVERSARY':
      return '#faad14';
    case 'CUSTOM':
      return '#52c41a';
    default:
      return '#1677ff';
  }
}

export default function CalendarPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const calendarRef = useRef<FullCalendar>(null);

  // Calendar state
  const [currentDate, setCurrentDate] = useState<string>(dayjs().format('YYYY-MM-DD'));
  const [eventTypeFilter, setEventTypeFilter] = useState<string | undefined>();

  // Event detail modal
  const [detailEvent, setDetailEvent] = useState<CalendarEvent | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Reschedule modal (for manual reschedule via detail modal)
  const [rescheduleEvent, setRescheduleEvent] = useState<CalendarEvent | null>(null);
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [rescheduleForm] = Form.useForm();

  // Holiday management
  const [holidayYear, setHolidayYear] = useState(dayjs().year());
  const [holidayModalOpen, setHolidayModalOpen] = useState(false);
  const [holidayForm] = Form.useForm();

  // Compute date range for API query (buffer around current month)
  const dateRange = useMemo(() => {
    const d = dayjs(currentDate);
    const start = d.startOf('month').subtract(7, 'day');
    const end = d.endOf('month').add(7, 'day');
    return {
      start_date: start.format('YYYY-MM-DD'),
      end_date: end.format('YYYY-MM-DD'),
      event_type: eventTypeFilter,
    };
  }, [currentDate, eventTypeFilter]);

  const { data: events, isLoading } = useCalendarEvents(dateRange);
  const { data: holidays, isLoading: holidaysLoading } = useHolidays(holidayYear);
  const rescheduleMutation = useRescheduleEvent();
  const updateHolidaysMutation = useUpdateHolidays();

  // Map CalendarEvent[] to FullCalendar EventInput[]
  const fullCalendarEvents: EventInput[] = useMemo(() => {
    if (!events) return [];
    return events.map((event) => ({
      id: event.id,
      title: event.title,
      start: event.scheduled_at || event.event_date,
      backgroundColor: getEventColor(event.event_type),
      borderColor: getEventColor(event.event_type),
      extendedProps: event,
    }));
  }, [events]);

  // FullCalendar: event click -> show detail modal
  const handleEventClick = useCallback((info: EventClickArg) => {
    const event = info.event.extendedProps as CalendarEvent;
    setDetailEvent(event);
    setDetailOpen(true);
  }, []);

  // FullCalendar: date click -> navigate to content creation
  const handleDateClick = useCallback(
    (info: DateClickArg) => {
      const dateStr = dayjs(info.date).format('YYYY-MM-DD');
      navigate(`/contents/create?date=${dateStr}`);
    },
    [navigate],
  );

  // FullCalendar: event drop (drag-and-drop reschedule)
  const handleEventDrop = useCallback(
    (info: EventDropArg) => {
      const calendarEvent = info.event.extendedProps as CalendarEvent;
      const newDate = info.event.start;
      if (!newDate) {
        info.revert();
        return;
      }

      const data: { event_date: string; scheduled_at?: string } = {
        event_date: dayjs(newDate).format('YYYY-MM-DD'),
      };
      // Preserve time if the event had a scheduled_at
      if (calendarEvent.scheduled_at) {
        data.scheduled_at = dayjs(newDate).toISOString();
      }

      rescheduleMutation.mutate(
        { id: calendarEvent.id, data },
        {
          onSuccess: () => {
            message.success(
              `"${calendarEvent.title}" 일정이 ${dayjs(newDate).format('YYYY-MM-DD')}로 변경되었습니다`,
            );
          },
          onError: () => {
            message.error('일정 변경에 실패했습니다');
            info.revert();
          },
        },
      );
    },
    [rescheduleMutation, message],
  );

  // FullCalendar: date range change -> update currentDate for API query
  const handleDatesSet = useCallback((dateInfo: { start: Date; end: Date }) => {
    // Use the midpoint of the visible range as current date
    const mid = new Date((dateInfo.start.getTime() + dateInfo.end.getTime()) / 2);
    setCurrentDate(dayjs(mid).format('YYYY-MM-DD'));
  }, []);

  // Handle manual reschedule from detail modal
  const handleReschedule = () => {
    if (!rescheduleEvent) return;
    rescheduleForm.validateFields().then((values) => {
      const data: { event_date: string; scheduled_at?: string } = {
        event_date: values.event_date.format('YYYY-MM-DD'),
      };
      if (values.scheduled_at) {
        data.scheduled_at = values.scheduled_at.toISOString();
      }
      rescheduleMutation.mutate(
        { id: rescheduleEvent.id, data },
        {
          onSuccess: () => {
            message.success('일정이 변경되었습니다');
            setRescheduleOpen(false);
            setRescheduleEvent(null);
            rescheduleForm.resetFields();
          },
          onError: () => message.error('일정 변경에 실패했습니다'),
        },
      );
    });
  };

  // Handle holiday form submission
  const handleAddHoliday = () => {
    holidayForm.validateFields().then((values) => {
      const currentHolidays = holidays || [];
      const newHoliday: HolidayCreateData = {
        event_type: 'HOLIDAY',
        title: values.title,
        description: values.description,
        event_date: values.event_date.format('YYYY-MM-DD'),
        is_holiday: true,
        is_recurring: values.is_recurring || false,
        color: '#ff4d4f',
      };
      const allHolidays: HolidayCreateData[] = [
        ...currentHolidays.map((h) => ({
          event_type: 'HOLIDAY' as const,
          title: h.title,
          description: h.description || undefined,
          event_date: h.event_date,
          is_holiday: true,
          is_recurring: h.is_recurring,
          color: h.color || '#ff4d4f',
        })),
        newHoliday,
      ];
      updateHolidaysMutation.mutate(allHolidays, {
        onSuccess: () => {
          message.success('공휴일이 추가되었습니다');
          setHolidayModalOpen(false);
          holidayForm.resetFields();
        },
        onError: () => message.error('공휴일 저장에 실패했습니다'),
      });
    });
  };

  // Delete holiday
  const handleDeleteHoliday = (eventId: string) => {
    const remainingHolidays = (holidays || [])
      .filter((h) => h.id !== eventId)
      .map((h) => ({
        event_type: 'HOLIDAY' as const,
        title: h.title,
        description: h.description || undefined,
        event_date: h.event_date,
        is_holiday: true,
        is_recurring: h.is_recurring,
        color: h.color || '#ff4d4f',
      }));
    updateHolidaysMutation.mutate(remainingHolidays, {
      onSuccess: () => message.success('공휴일이 삭제되었습니다'),
      onError: () => message.error('공휴일 삭제에 실패했습니다'),
    });
  };

  // Holiday table columns
  const holidayColumns: ColumnsType<CalendarEvent> = [
    {
      title: '날짜',
      dataIndex: 'event_date',
      key: 'event_date',
      width: 130,
      sorter: (a, b) => a.event_date.localeCompare(b.event_date),
      render: (d: string) => dayjs(d).format('YYYY-MM-DD'),
    },
    {
      title: '공휴일명',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '반복',
      dataIndex: 'is_recurring',
      key: 'is_recurring',
      width: 80,
      render: (v: boolean) => (v ? <Tag color="blue">매년</Tag> : <Tag>단발</Tag>),
    },
    {
      title: '관리',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Button
          type="text"
          size="small"
          danger
          icon={<Trash2 size={14} />}
          onClick={() => handleDeleteHoliday(record.id)}
          title="삭제"
        />
      ),
    },
  ];

  return (
    <div>
      {/* Page Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CalendarIcon size={24} />
          <Title level={4} className="!mb-0">
            캘린더
          </Title>
        </div>
      </div>

      <Tabs
        defaultActiveKey="calendar"
        items={[
          {
            key: 'calendar',
            label: '캘린더',
            children: (
              <div>
                {/* Event type filter */}
                <div className="mb-4 flex items-center gap-3">
                  <Select
                    placeholder="이벤트 타입"
                    allowClear
                    style={{ width: 160 }}
                    onChange={(v) => setEventTypeFilter(v)}
                    options={Object.entries(EVENT_TYPE_CONFIG).map(([value, { text }]) => ({
                      value,
                      label: text,
                    }))}
                  />
                </div>

                {/* FullCalendar */}
                <Card loading={isLoading}>
                  <FullCalendar
                    ref={calendarRef}
                    plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                    initialView="dayGridMonth"
                    locale="ko"
                    headerToolbar={{
                      left: 'prev,next today',
                      center: 'title',
                      right: 'dayGridMonth,timeGridWeek,timeGridDay',
                    }}
                    buttonText={{
                      today: '오늘',
                      month: '월간',
                      week: '주간',
                      day: '일간',
                    }}
                    events={fullCalendarEvents}
                    editable
                    selectable
                    dayMaxEvents={3}
                    eventClick={handleEventClick}
                    dateClick={handleDateClick}
                    eventDrop={handleEventDrop}
                    datesSet={handleDatesSet}
                    height="auto"
                  />
                </Card>
              </div>
            ),
          },
          {
            key: 'holidays',
            label: '공휴일 관리',
            children: (
              <div>
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Select
                      value={holidayYear}
                      onChange={setHolidayYear}
                      style={{ width: 120 }}
                      options={Array.from({ length: 5 }, (_, i) => {
                        const y = dayjs().year() - 1 + i;
                        return { value: y, label: `${y}년` };
                      })}
                    />
                    <Text type="secondary">
                      총 {holidays?.length || 0}개의 공휴일
                    </Text>
                  </div>
                  <Button
                    type="primary"
                    icon={<Plus size={14} />}
                    onClick={() => setHolidayModalOpen(true)}
                  >
                    공휴일 추가
                  </Button>
                </div>

                <Table
                  columns={holidayColumns}
                  dataSource={holidays || []}
                  rowKey="id"
                  loading={holidaysLoading || updateHolidaysMutation.isPending}
                  pagination={false}
                />
              </div>
            ),
          },
        ]}
      />

      {/* Event Detail Modal */}
      <Modal
        title="일정 상세"
        open={detailOpen}
        onCancel={() => {
          setDetailOpen(false);
          setDetailEvent(null);
        }}
        footer={
          detailEvent && !detailEvent.is_holiday ? (
            <Space>
              <Button
                onClick={() => {
                  setDetailOpen(false);
                  setRescheduleEvent(detailEvent);
                  rescheduleForm.setFieldsValue({
                    event_date: dayjs(detailEvent.event_date),
                    scheduled_at: detailEvent.scheduled_at
                      ? dayjs(detailEvent.scheduled_at)
                      : undefined,
                  });
                  setRescheduleOpen(true);
                }}
              >
                일정 변경
              </Button>
              {detailEvent.content_id && (
                <Button
                  type="primary"
                  onClick={() => {
                    setDetailOpen(false);
                    navigate(`/contents/${detailEvent.content_id}`);
                  }}
                >
                  콘텐츠 보기
                </Button>
              )}
              <Button onClick={() => setDetailOpen(false)}>닫기</Button>
            </Space>
          ) : null
        }
        width={560}
      >
        {detailEvent && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="제목">{detailEvent.title}</Descriptions.Item>
            <Descriptions.Item label="타입">
              <Tag
                color={
                  EVENT_TYPE_CONFIG[detailEvent.event_type]?.color || 'default'
                }
              >
                {EVENT_TYPE_CONFIG[detailEvent.event_type]?.text || detailEvent.event_type}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="날짜">
              {dayjs(detailEvent.event_date).format('YYYY-MM-DD')}
            </Descriptions.Item>
            {detailEvent.scheduled_at && (
              <Descriptions.Item label="예약 시간">
                {dayjs(detailEvent.scheduled_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
            )}
            {detailEvent.platform && (
              <Descriptions.Item label="플랫폼">
                <Tag color={getPlatformConfig(detailEvent.platform).color}>{getPlatformConfig(detailEvent.platform).label}</Tag>
              </Descriptions.Item>
            )}
            {detailEvent.description && (
              <Descriptions.Item label="설명">
                <div style={{ whiteSpace: 'pre-wrap' }}>{detailEvent.description}</div>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="상태">{detailEvent.status}</Descriptions.Item>
            {detailEvent.is_holiday && (
              <Descriptions.Item label="공휴일">
                <Tag color="red">공휴일</Tag>
              </Descriptions.Item>
            )}
            {detailEvent.is_recurring && (
              <Descriptions.Item label="반복">
                <Tag color="blue">매년 반복</Tag>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* Reschedule Modal */}
      <Modal
        title="일정 변경"
        open={rescheduleOpen}
        onCancel={() => {
          setRescheduleOpen(false);
          setRescheduleEvent(null);
          rescheduleForm.resetFields();
        }}
        onOk={handleReschedule}
        okText="변경"
        cancelText="취소"
        confirmLoading={rescheduleMutation.isPending}
      >
        {rescheduleEvent && (
          <div>
            <div className="mb-4 rounded bg-gray-50 p-3">
              <Text strong>{rescheduleEvent.title}</Text>
              <br />
              <Text type="secondary">
                현재: {dayjs(rescheduleEvent.event_date).format('YYYY-MM-DD')}
                {rescheduleEvent.scheduled_at &&
                  ` ${dayjs(rescheduleEvent.scheduled_at).format('HH:mm')}`}
              </Text>
            </div>
            <Form form={rescheduleForm} layout="vertical">
              <Form.Item
                name="event_date"
                label="새로운 날짜"
                rules={[{ required: true, message: '날짜를 선택하세요' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="scheduled_at" label="예약 시간 (선택)">
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
            </Form>
          </div>
        )}
      </Modal>

      {/* Add Holiday Modal */}
      <Modal
        title="공휴일 추가"
        open={holidayModalOpen}
        onCancel={() => {
          setHolidayModalOpen(false);
          holidayForm.resetFields();
        }}
        onOk={handleAddHoliday}
        okText="추가"
        cancelText="취소"
        confirmLoading={updateHolidaysMutation.isPending}
      >
        <Form form={holidayForm} layout="vertical">
          <Form.Item
            name="title"
            label="공휴일명"
            rules={[{ required: true, message: '공휴일명을 입력하세요' }]}
          >
            <Input placeholder="예: 설날, 추석, 개천절" />
          </Form.Item>
          <Form.Item name="description" label="설명">
            <Input.TextArea rows={2} placeholder="공휴일 설명 (선택)" />
          </Form.Item>
          <Form.Item
            name="event_date"
            label="날짜"
            rules={[{ required: true, message: '날짜를 선택하세요' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_recurring" label="매년 반복">
            <Select
              options={[
                { value: false, label: '단발성' },
                { value: true, label: '매년 반복' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
