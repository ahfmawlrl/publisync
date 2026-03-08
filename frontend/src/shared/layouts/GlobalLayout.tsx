import { Layout } from 'antd';
import { useEffect, useState } from 'react';
import { Outlet } from 'react-router';

import { useUiStore } from '@/shared/stores/useUiStore';
import MobileTabBar from './MobileTabBar';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

const { Content } = Layout;

const MOBILE_BREAKPOINT = 768;

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < MOBILE_BREAKPOINT);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return isMobile;
}

export default function GlobalLayout() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const isMobile = useIsMobile();

  return (
    <Layout className="min-h-screen">
      <Sidebar isMobile={isMobile} />
      <Layout>
        <TopBar isMobile={isMobile} />
        <Content
          className="p-6"
          style={{
            marginLeft: isMobile ? 0 : collapsed ? 80 : 240,
            marginTop: 64,
            paddingBottom: isMobile ? 72 : undefined,
            transition: 'margin-left 0.2s',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
      {isMobile && <MobileTabBar />}
    </Layout>
  );
}
