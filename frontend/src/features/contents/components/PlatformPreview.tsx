import { Card, Tag, Typography } from 'antd';

const { Text } = Typography;

interface PlatformPreviewProps {
  platform: string;
  title: string;
  body: string;
  hashtags: string[];
}

const PLATFORM_CONFIG: Record<string, { label: string; color: string; maxBody: number; aspect: string }> = {
  YOUTUBE: { label: 'YouTube', color: 'red', maxBody: 60, aspect: '16:9' },
  INSTAGRAM: { label: 'Instagram', color: 'purple', maxBody: 80, aspect: '1:1' },
  FACEBOOK: { label: 'Facebook', color: 'blue', maxBody: 100, aspect: '16:9' },
  X: { label: 'X (Twitter)', color: 'default', maxBody: 280, aspect: '16:9' },
  NAVER_BLOG: { label: '네이버 블로그', color: 'green', maxBody: 120, aspect: '16:9' },
};

export default function PlatformPreview({ platform, title, body, hashtags }: PlatformPreviewProps) {
  const cfg = PLATFORM_CONFIG[platform] || { label: platform, color: 'default', maxBody: 100, aspect: '16:9' };

  const aspectClass = cfg.aspect === '1:1' ? 'aspect-square' : 'aspect-video';

  return (
    <Card size="small" className="h-full">
      <Tag color={cfg.color} className="mb-2">{cfg.label}</Tag>
      <div className={`mb-2 flex items-center justify-center rounded bg-gray-100 text-gray-400 text-xs ${aspectClass}`}>
        미디어 미리보기
      </div>
      {platform !== 'X' && (
        <>
          <Text strong className="text-sm line-clamp-1">{title || '제목 미입력'}</Text>
          <br />
        </>
      )}
      <Text type="secondary" className="text-xs line-clamp-3">
        {(body || '').slice(0, cfg.maxBody) || '본문 미입력'}
      </Text>
      {hashtags.length > 0 && (
        <div className="mt-1">
          <Text className="text-xs" style={{ color: '#1677ff' }}>
            {hashtags.map((h) => (h.startsWith('#') ? h : `#${h}`)).join(' ')}
          </Text>
        </div>
      )}
    </Card>
  );
}
