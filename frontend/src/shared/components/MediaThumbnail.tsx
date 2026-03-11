import { Image } from 'antd';
import { useCallback, useState } from 'react';

/** SVG placeholder shown when an image fails to load. */
const FALLBACK_SVG = `data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
    <rect width="160" height="160" fill="#f5f5f5"/>
    <text x="80" y="90" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#bfbfbf">이미지 없음</text>
  </svg>`,
)}`;

interface MediaThumbnailProps {
  src: string;
  alt?: string;
  width?: number;
  height?: number;
}

/**
 * Image thumbnail with graceful error handling.
 * Shows a placeholder when the source fails to load and disables preview.
 */
export default function MediaThumbnail({ src, alt = '미디어', width = 160, height = 160 }: MediaThumbnailProps) {
  const [errored, setErrored] = useState(false);

  const handleError = useCallback(() => {
    setErrored(true);
  }, []);

  return (
    <Image
      src={src}
      alt={alt}
      width={width}
      height={height}
      className="rounded object-cover"
      fallback={FALLBACK_SVG}
      preview={!errored}
      onError={handleError}
    />
  );
}
