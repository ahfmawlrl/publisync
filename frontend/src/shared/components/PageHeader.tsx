import { Typography } from 'antd';

const { Title, Text } = Typography;

interface PageHeaderProps {
  title: string;
  subtitle?: string;
}

export default function PageHeader({ title, subtitle }: PageHeaderProps) {
  return (
    <div className="mb-4">
      <Title level={4} className="!mb-0">
        {title}
      </Title>
      {subtitle && (
        <Text type="secondary" className="text-sm">
          {subtitle}
        </Text>
      )}
    </div>
  );
}
