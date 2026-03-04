import { describe, expect, it } from 'vitest';

// Basic type check tests (hooks require QueryClient provider, so we test types)
describe('Dashboard hooks types', () => {
  it('should export the expected hooks', async () => {
    const mod = await import('./useDashboard');
    expect(typeof mod.useDashboardSummary).toBe('function');
    expect(typeof mod.useRecentContents).toBe('function');
    expect(typeof mod.useTodaySchedule).toBe('function');
    expect(typeof mod.useApprovalStatus).toBe('function');
    expect(typeof mod.useSentimentSummary).toBe('function');
    expect(typeof mod.usePlatformTrends).toBe('function');
  });
});
