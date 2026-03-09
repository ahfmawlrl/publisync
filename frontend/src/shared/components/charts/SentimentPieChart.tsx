import type { PieLabelRenderProps } from 'recharts';
import { Cell, Legend, Pie, PieChart, Tooltip } from 'recharts';

import ChartContainer from './ChartContainer';

const SENTIMENT_COLORS: Record<string, string> = {
  POSITIVE: '#52c41a',
  NEUTRAL: '#1677ff',
  NEGATIVE: '#faad14',
  DANGEROUS: '#ff4d4f',
};

const SENTIMENT_LABELS: Record<string, string> = {
  POSITIVE: '긍정',
  NEUTRAL: '중립',
  NEGATIVE: '부정',
  DANGEROUS: '위험',
};

interface SentimentPieChartProps {
  data: Array<{ sentiment: string; count: number }>;
}

export default function SentimentPieChart({ data }: SentimentPieChartProps) {
  const chartData = data.map((item) => ({
    name: SENTIMENT_LABELS[item.sentiment] || item.sentiment,
    value: item.count,
    sentiment: item.sentiment,
  }));

  return (
    <ChartContainer empty={!data || data.length === 0} emptyText="감성 분석 데이터가 없습니다">
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
          label={(props: PieLabelRenderProps) =>
            `${String(props.name ?? '')} ${(((props.percent as number | undefined) ?? 0) * 100).toFixed(0)}%`
          }
        >
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={SENTIMENT_COLORS[entry.sentiment] || '#8884d8'}
            />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ChartContainer>
  );
}
