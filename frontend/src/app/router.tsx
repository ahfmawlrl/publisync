import { lazy, Suspense } from 'react';
import { createBrowserRouter } from 'react-router';
import { Spin } from 'antd';

import RouteGuard from '@/shared/components/RouteGuard';
import PlaceholderPage from '@/shared/components/PlaceholderPage';
import GlobalLayout from '@/shared/layouts/GlobalLayout';
import type { Role } from '@/shared/types';

const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'));
const ResetPasswordPage = lazy(() => import('@/features/auth/pages/ResetPasswordPage'));
const InvitePage = lazy(() => import('@/features/auth/pages/InvitePage'));
const DashboardPage = lazy(() => import('@/features/dashboard/pages/DashboardPage'));
const UsersPage = lazy(() => import('@/features/settings/pages/UsersPage'));
const OrganizationsPage = lazy(() => import('@/features/settings/pages/OrganizationsPage'));
const ChannelsPage = lazy(() => import('@/features/channels/pages/ChannelsPage'));
const ContentsListPage = lazy(() => import('@/features/contents/pages/ContentsListPage'));
const ContentCreatePage = lazy(() => import('@/features/contents/pages/ContentCreatePage'));
const ContentDetailPage = lazy(() => import('@/features/contents/pages/ContentDetailPage'));
const ContentEditPage = lazy(() => import('@/features/contents/pages/ContentEditPage'));
const ApprovalsListPage = lazy(() => import('@/features/approvals/pages/ApprovalsListPage'));
const WorkflowSettingsPage = lazy(() => import('@/features/approvals/pages/WorkflowSettingsPage'));
const CommentsListPage = lazy(() => import('@/features/comments/pages/CommentsListPage'));
const DangerousCommentsPage = lazy(() => import('@/features/comments/pages/DangerousCommentsPage'));
const AuditLogsPage = lazy(() => import('@/features/audit/pages/AuditLogsPage'));
const AnalyticsPage = lazy(() => import('@/features/analytics/pages/AnalyticsPage'));
const NotificationsPage = lazy(() => import('@/features/notifications/pages/NotificationsPage'));
const CalendarPage = lazy(() => import('@/features/calendar/pages/CalendarPage'));
const MediaLibraryPage = lazy(() => import('@/features/media/pages/MediaLibraryPage'));
const SubtitleEditorPage = lazy(() => import('@/features/ai/pages/SubtitleEditorPage'));
const ShortformEditorPage = lazy(() => import('@/features/ai/pages/ShortformEditorPage'));
const ReportsPage = lazy(() => import('@/features/reports/pages/ReportsPage'));
const SentimentTrendPage = lazy(() => import('@/features/analytics/pages/SentimentTrendPage'));
const PredictionPage = lazy(() => import('@/features/analytics/pages/PredictionPage'));
const BenchmarkPage = lazy(() => import('@/features/analytics/pages/BenchmarkPage'));
const ReplyTemplatesPage = lazy(() => import('@/features/comments/pages/ReplyTemplatesPage'));
const NotificationSettingsPage = lazy(
  () => import('@/features/notifications/pages/NotificationSettingsPage'),
);
const ChannelHistoryPage = lazy(() => import('@/features/channels/pages/ChannelHistoryPage'));

// RBAC role shortcuts
const SA: Role = 'SYSTEM_ADMIN';
const AM: Role = 'AGENCY_MANAGER';
const AO: Role = 'AGENCY_OPERATOR';
const CD: Role = 'CLIENT_DIRECTOR';


function SuspenseLoader() {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
      }}
    >
      <Spin size="large" />
    </div>
  );
}

function withSuspense(Component: React.LazyExoticComponent<() => React.JSX.Element>) {
  return (
    <Suspense fallback={<SuspenseLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  // ── Public routes ──────────────────────────────────────
  {
    path: '/login',
    element: withSuspense(LoginPage),
  },
  {
    path: '/reset-password',
    element: withSuspense(ResetPasswordPage),
  },
  {
    path: '/invite',
    element: withSuspense(InvitePage),
  },

  // ── Protected routes (with layout) ────────────────────
  {
    element: <RouteGuard />,
    children: [
      {
        element: <GlobalLayout />,
        children: [
          // Dashboard — all roles
          { path: '/', element: withSuspense(DashboardPage) },

          // ── Contents (AM, AO, CD) ──
          {
            element: <RouteGuard requiredRoles={[AM, AO, CD]} />,
            children: [
              { path: '/contents', element: withSuspense(ContentsListPage) },
              { path: '/contents/:id', element: withSuspense(ContentDetailPage) },
              { path: '/approvals', element: withSuspense(ApprovalsListPage) },
              { path: '/calendar', element: withSuspense(CalendarPage) },
            ],
          },
          // Contents create/edit — AM, AO only
          {
            element: <RouteGuard requiredRoles={[AM, AO]} />,
            children: [
              { path: '/contents/create', element: withSuspense(ContentCreatePage) },
              { path: '/contents/:id/edit', element: withSuspense(ContentEditPage) },
            ],
          },

          // ── Comments (AM, AO, CD) ──
          {
            element: <RouteGuard requiredRoles={[AM, AO, CD]} />,
            children: [
              { path: '/comments', element: withSuspense(CommentsListPage) },
              { path: '/comments/dangerous', element: withSuspense(DangerousCommentsPage) },
            ],
          },
          // Reply templates — AM, AO only
          {
            element: <RouteGuard requiredRoles={[AM, AO]} />,
            children: [
              { path: '/comments/reply-templates', element: withSuspense(ReplyTemplatesPage) },
            ],
          },

          // ── Media (AM, AO, CD) ──
          {
            element: <RouteGuard requiredRoles={[AM, AO, CD]} />,
            children: [
              { path: '/media', element: withSuspense(MediaLibraryPage) },
            ],
          },

          // ── Analytics & Reports (AM, AO, CD) ──
          {
            element: <RouteGuard requiredRoles={[AM, AO, CD]} />,
            children: [
              { path: '/analytics', element: withSuspense(AnalyticsPage) },
              { path: '/analytics/sentiment', element: withSuspense(SentimentTrendPage) },
              { path: '/analytics/prediction', element: withSuspense(PredictionPage) },
              { path: '/analytics/benchmark', element: withSuspense(BenchmarkPage) },
              { path: '/reports', element: withSuspense(ReportsPage) },
            ],
          },

          // ── Channels (SA, AM) ──
          {
            element: <RouteGuard requiredRoles={[SA, AM]} />,
            children: [
              { path: '/channels', element: withSuspense(ChannelsPage) },
              { path: '/channels/history', element: withSuspense(ChannelHistoryPage) },
            ],
          },

          // ── Settings: Users & Orgs (SA, AM) ──
          {
            element: <RouteGuard requiredRoles={[SA, AM]} />,
            children: [
              { path: '/users', element: withSuspense(UsersPage) },
              { path: '/settings/organizations', element: withSuspense(OrganizationsPage) },
            ],
          },
          // Workflow settings (SA, AM, CD)
          {
            element: <RouteGuard requiredRoles={[SA, AM, CD]} />,
            children: [
              { path: '/approvals/settings', element: withSuspense(WorkflowSettingsPage) },
            ],
          },
          // Audit logs (SA, AM, CD)
          {
            element: <RouteGuard requiredRoles={[SA, AM, CD]} />,
            children: [
              { path: '/audit-logs', element: withSuspense(AuditLogsPage) },
            ],
          },

          // ── Notifications & Settings — all roles ──
          { path: '/notifications', element: withSuspense(NotificationsPage) },
          { path: '/settings/notifications', element: withSuspense(NotificationSettingsPage) },

          // ── AI tools (AM, AO) ──
          {
            element: <RouteGuard requiredRoles={[AM, AO]} />,
            children: [
              { path: '/ai/subtitle-editor/:assetId', element: withSuspense(SubtitleEditorPage) },
              { path: '/ai/shortform-editor/:assetId', element: withSuspense(ShortformEditorPage) },
            ],
          },

          // ── Help — all roles ──
          { path: '/help', element: <PlaceholderPage title="도움말" sprint="Phase 2" /> },
        ],
      },
    ],
  },
]);
