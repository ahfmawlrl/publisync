import { Layout } from 'antd';
import { Outlet } from 'react-router';

import { useUiStore } from '@/shared/stores/useUiStore';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

const { Content } = Layout;

export default function GlobalLayout() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);

  return (
    <Layout className="min-h-screen">
      <Sidebar />
      <Layout>
        <TopBar />
        <Content
          className="p-6"
          style={{ marginLeft: collapsed ? 80 : 240, marginTop: 64, transition: 'margin-left 0.2s' }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
