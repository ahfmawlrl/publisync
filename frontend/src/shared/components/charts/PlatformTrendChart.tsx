import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts';

import ChartContainer from './ChartContainer';

export type MetricKey = 'views' | 'likes' | 'shares';

const METRIC_LINE_CONFIG: Record<MetricKey, { name: string; color: string }> = {
  views: { name: '조회수', color: '#1677ff' },
  likes: { name: '좋아요', color: '#52c41a' },
  shares: { name: '공유', color: '#faad14' },
};

interface TrendDataItem {
  platform: string;
  views: number;
  likes: number;
  shares: number;
}

interface PlatformTrendChartProps {
  data: TrendDataItem[];
  visibleMetrics: MetricKey[];
}

export default function PlatformTrendChart({ data, visibleMetrics }: PlatformTrendChartProps) {
  return (
    <ChartContainer empty={!data || data.length === 0} emptyText="플랫폼 데이터가 없습니다">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="platform" />
        <YAxis />
        <Tooltip />
        <Legend />
        {visibleMetrics.map((key) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            name={METRIC_LINE_CONFIG[key].name}
            stroke={METRIC_LINE_CONFIG[key].color}
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
