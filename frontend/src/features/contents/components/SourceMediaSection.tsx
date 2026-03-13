import { Card } from 'antd';

import MediaUpload from '@/shared/components/MediaUpload';

interface SourceMediaSectionProps {
  value?: string[];
  onChange?: (urls: string[]) => void;
  maxFiles?: number;
}

/**
 * 소재 준비 섹션: 콘텐츠 에디터 상단에 배치.
 * MediaUpload(드래그 업로드 + 미디어 라이브러리 Picker)를 Card로 래핑.
 */
export default function SourceMediaSection({
  value,
  onChange,
  maxFiles = 10,
}: SourceMediaSectionProps) {
  return (
    <Card title="미디어 소재" size="small">
      <MediaUpload value={value} onChange={onChange} maxFiles={maxFiles} />
    </Card>
  );
}
