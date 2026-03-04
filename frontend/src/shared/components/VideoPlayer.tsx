import { useEffect, useRef } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import type Player from 'video.js/dist/types/player';

interface VideoPlayerProps {
  src: string;
  type?: string;
  poster?: string;
  subtitles?: { src: string; srclang: string; label: string }[];
  onTimeUpdate?: (currentTime: number) => void;
  onReady?: (player: Player) => void;
  className?: string;
}

export default function VideoPlayer({
  src,
  type,
  poster,
  subtitles,
  onTimeUpdate,
  onReady,
  className,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<Player | null>(null);

  useEffect(() => {
    if (!videoRef.current) return;

    const videoElement = document.createElement('video-js');
    videoElement.classList.add('vjs-big-play-centered');
    videoRef.current.appendChild(videoElement);

    const player = videojs(videoElement, {
      controls: true,
      responsive: true,
      fluid: true,
      sources: [{ src, type: type || 'video/mp4' }],
      poster,
    });

    if (subtitles) {
      subtitles.forEach((sub) => {
        player.addRemoteTextTrack({ kind: 'subtitles', ...sub }, false);
      });
    }

    if (onTimeUpdate) {
      player.on('timeupdate', () => onTimeUpdate(player.currentTime() ?? 0));
    }

    if (onReady) {
      player.ready(() => onReady(player));
    }

    playerRef.current = player;

    return () => {
      if (playerRef.current && !playerRef.current.isDisposed()) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-create player when src changes
  }, [src]);

  return <div ref={videoRef} className={className} data-vjs-player />;
}
