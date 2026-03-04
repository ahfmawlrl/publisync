import { Result, Spin } from 'antd';
import { Navigate, Outlet } from 'react-router';

import { useAuthStore } from '@/shared/stores/useAuthStore';
import { useWorkspace } from '@/shared/hooks/useWorkspace';
import type { Role } from '@/shared/types';

interface RouteGuardProps {
  requiredRoles?: Role[];
}

/**
 * Route guard — checks:
 * 1. Authentication (accessToken exists)
 * 2. Role authorization (requiredRoles)
 * 3. Workspace context (currentOrgId must be set)
 */
export default function RouteGuard({ requiredRoles }: RouteGuardProps) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const { currentOrgId, isLoading: wsLoading } = useWorkspace();

  // 1. Not authenticated → redirect to login
  if (!accessToken || !user) {
    return <Navigate to="/login" replace />;
  }

  // 2. Role check
  if (requiredRoles && requiredRoles.length > 0) {
    const hasRole = requiredRoles.includes(user.role as Role);
    if (!hasRole) {
      return (
        <Result status="403" title="접근 권한이 없습니다" subTitle="이 페이지에 접근할 권한이 부족합니다." />
      );
    }
  }

  // 3. Workspace context — wait for workspace list, then require selection
  if (wsLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="워크스페이스 로딩 중..." />
      </div>
    );
  }

  if (!currentOrgId) {
    return (
      <Result
        status="warning"
        title="워크스페이스를 선택하세요"
        subTitle="접근 가능한 워크스페이스가 없습니다. 관리자에게 문의하세요."
      />
    );
  }

  return <Outlet />;
}
