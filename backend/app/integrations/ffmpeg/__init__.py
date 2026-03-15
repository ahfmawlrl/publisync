"""ffmpeg 유틸리티 모듈 — 영상 편집 파이프라인.

영상 메타데이터 추출, 썸네일 생성, 자막 합성, 구간 절단, 오디오 믹싱 등
ffmpeg 기반 영상 처리 기능의 통합 진입점.

Usage::

    from app.integrations.ffmpeg import probe_metadata, burn_subtitles, trim_segment
    from app.integrations.ffmpeg import SubtitleSegment, SubtitleStyle

    # 메타데이터 추출
    meta = probe_metadata("/tmp/video.mp4")

    # 자막 합성
    result = burn_subtitles("/tmp/video.mp4", "/tmp/output.mp4", "/tmp/subs.srt")

    # 숏폼 절단
    result = trim_segment("/tmp/video.mp4", "/tmp/short.mp4", start=30.0, end=75.0)
"""

from .audio import mix_audio, replace_audio
from .common import (
    FFmpegError,
    FFmpegNotInstalledError,
    FFmpegResult,
    SubtitleSegment,
    SubtitleStyle,
    TrimSegment,
    VideoMetadata,
    calculate_timeout,
    check_ffmpeg_installed,
    check_ffprobe_installed,
    parse_progress,
    seconds_to_srt_time,
)
from .probe import get_duration, probe_metadata
from .subtitle import burn_subtitles, generate_srt
from .thumbnail import extract_frame, extract_frames_multi
from .trim import trim_segment

__all__ = [
    "FFmpegError",
    "FFmpegNotInstalledError",
    "FFmpegResult",
    "SubtitleSegment",
    "SubtitleStyle",
    "TrimSegment",
    "VideoMetadata",
    "burn_subtitles",
    "calculate_timeout",
    "check_ffmpeg_installed",
    "check_ffprobe_installed",
    "extract_frame",
    "extract_frames_multi",
    "generate_srt",
    "get_duration",
    "mix_audio",
    "parse_progress",
    "probe_metadata",
    "replace_audio",
    "seconds_to_srt_time",
    "trim_segment",
]
