/**
 * AuthImage — JWT 인증이 필요한 이미지를 로드하는 컴포넌트.
 *
 * 브라우저 네이티브 <img> 태그는 Authorization 헤더를 보내지 않으므로,
 * Axios 인터셉터를 통해 이미지를 fetch한 뒤 blob URL로 변환하여 표시한다.
 */
import { useEffect, useRef, useState } from 'react';

import apiClient from '@/shared/api/client';

interface AuthImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  /** API 경로 (예: `/media/${id}/thumbnail`) — `/api/v1` 접두사 제외 */
  src: string;
  /** 로딩 중 또는 실패 시 보여줄 fallback */
  fallback?: React.ReactNode;
}

export default function AuthImage({ src, fallback, alt, ...imgProps }: AuthImageProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const res = await apiClient.get(src, { responseType: 'blob' });
        if (cancelled) return;
        const url = URL.createObjectURL(res.data as Blob);
        urlRef.current = url;
        setBlobUrl(url);
        setError(false);
      } catch {
        if (!cancelled) setError(true);
      }
    };

    setBlobUrl(null);
    setError(false);
    load();

    return () => {
      cancelled = true;
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
        urlRef.current = null;
      }
    };
  }, [src]);

  if (error) {
    return fallback ? <>{fallback}</> : null;
  }

  if (!blobUrl) {
    return fallback ? <>{fallback}</> : null;
  }

  return <img src={blobUrl} alt={alt} {...imgProps} />;
}
