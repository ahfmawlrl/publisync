import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import type Player from 'video.js/dist/types/player';

export interface VideoPlayerHandle {
  seekTo: (time: number) => void;
  getCurrentTime: () => number;
  getPlayer: () => Player | null;
}

interface VideoPlayerProps {
  src: string;
  type?: string;
  poster?: string;
  subtitles?: { src: string; srclang: string; label: string }[];
  onTimeUpdate?: (currentTime: number) => void;
  onReady?: (player: Player) => void;
  className?: string;
}

const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(function VideoPlayer(
  { src, type, poster, subtitles, onTimeUpdate, onReady, className },
  ref,
) {
  const videoRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<Player | null>(null);

  useImperativeHandle(ref, () => ({
    seekTo(time: number) {
      if (playerRef.current && !playerRef.current.isDisposed()) {
        playerRef.current.currentTime(time);
      }
    },
    getCurrentTime() {
      if (playerRef.current && !playerRef.current.isDisposed()) {
        return playerRef.current.currentTime() ?? 0;
      }
      return 0;
    },
    getPlayer() {
      return playerRef.current;
    },
  }));

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
});

export default VideoPlayer;
