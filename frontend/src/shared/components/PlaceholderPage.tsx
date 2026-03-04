import { Result } from 'antd';

interface PlaceholderPageProps {
  title: string;
  sprint?: string;
}

export default function PlaceholderPage({ title, sprint }: PlaceholderPageProps) {
  return (
    <Result
      status="info"
      title={title}
      subTitle={sprint ? `${sprint}에서 구현 예정입니다.` : '준비 중입니다.'}
    />
  );
}
