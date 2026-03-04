import { useEffect, useRef } from 'react';
import WaveSurfer from 'wavesurfer.js';

interface WaveformViewerProps {
  audioUrl: string;
  height?: number;
  waveColor?: string;
  progressColor?: string;
  onTimeUpdate?: (currentTime: number) => void;
  onReady?: (wavesurfer: WaveSurfer) => void;
  className?: string;
}

export default function WaveformViewer({
  audioUrl,
  height = 80,
  waveColor = '#1677ff',
  progressColor = '#096dd9',
  onTimeUpdate,
  onReady,
  className,
}: WaveformViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WaveSurfer | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      height,
      waveColor,
      progressColor,
      url: audioUrl,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
    });

    if (onTimeUpdate) {
      ws.on('timeupdate', (time) => onTimeUpdate(time));
    }

    if (onReady) {
      ws.on('ready', () => onReady(ws));
    }

    wsRef.current = ws;

    return () => {
      ws.destroy();
      wsRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-create waveform when audioUrl changes
  }, [audioUrl]);

  return <div ref={containerRef} className={className} />;
}
