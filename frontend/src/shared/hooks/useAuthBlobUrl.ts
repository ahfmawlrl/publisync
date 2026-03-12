/**
 * useAuthBlobUrl — JWT 인증이 필요한 리소스를 blob URL로 변환하는 훅.
 *
 * <video>, <audio>, <img> 등 브라우저 네이티브 태그는 Authorization 헤더를
 * 보내지 않으므로, Axios로 fetch한 뒤 blob URL로 변환하여 전달한다.
 */
import { useEffect, useRef, useState } from 'react';

import apiClient from '@/shared/api/client';

export default function useAuthBlobUrl(src: string | null) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!src) {
      setBlobUrl(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(false);

    const load = async () => {
      try {
        const res = await apiClient.get(src, { responseType: 'blob' });
        if (cancelled) return;
        const url = URL.createObjectURL(res.data as Blob);
        urlRef.current = url;
        setBlobUrl(url);
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
        urlRef.current = null;
      }
    };
  }, [src]);

  return { blobUrl, loading, error };
}
