import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';
import { formatDate, formatDateTime, truncateText } from './format';

describe('format utils', () => {
  it('formatDate should format ISO string', () => {
    expect(formatDate('2024-03-15T10:30:00Z')).toBe('2024-03-15');
  });

  it('formatDateTime should include date and time', () => {
    const input = '2024-03-15T10:30:00Z';
    const result = formatDateTime(input);
    // Use dayjs to compute expected local time (timezone-independent)
    const expected = dayjs(input).format('YYYY-MM-DD HH:mm');
    expect(result).toBe(expected);
  });

  it('truncateText should truncate long text', () => {
    expect(truncateText('hello', 10)).toBe('hello');
    expect(truncateText('hello world', 5)).toBe('hello...');
  });
});
