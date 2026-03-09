import { Spin, Typography } from 'antd';
import type { ReactElement } from 'react';
import { ResponsiveContainer } from 'recharts';

const { Text } = Typography;

interface ChartContainerProps {
  height?: number;
  loading?: boolean;
  empty?: boolean;
  emptyText?: string;
  children: ReactElement;
}

export default function ChartContainer({
  height = 240,
  loading = false,
  empty = false,
  emptyText = '데이터가 없습니다',
  children,
}: ChartContainerProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <Spin />
      </div>
    );
  }

  if (empty) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <Text type="secondary">{emptyText}</Text>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      {children}
    </ResponsiveContainer>
  );
}
