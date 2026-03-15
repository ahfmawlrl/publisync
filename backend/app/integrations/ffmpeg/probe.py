"""ffprobe 기반 영상 메타데이터 추출."""

from __future__ import annotations

import json
import subprocess

import structlog

from .common import (
    FFmpegError,
    FFmpegNotInstalledError,
    VideoMetadata,
    check_ffprobe_installed,
)

logger = structlog.get_logger()


def probe_metadata(input_path: str) -> VideoMetadata:
    """ffprobe로 영상 메타데이터를 추출한다.

    Args:
        input_path: 로컬 영상 파일 경로.

    Returns:
        VideoMetadata 객체.

    Raises:
        FFmpegNotInstalledError: ffprobe가 설치되지 않은 경우.
        FFmpegError: ffprobe 실행 실패.
    """
    if not check_ffprobe_installed():
        raise FFmpegNotInstalledError("ffprobe is not installed or not in PATH")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        input_path,
    ]

    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired as e:
        raise FFmpegError("ffprobe timed out", command=" ".join(cmd)) from e

    if result.returncode != 0:
        raise FFmpegError(
            f"ffprobe failed with code {result.returncode}",
            command=" ".join(cmd),
            stderr=result.stderr[:500],
        )

    probe = json.loads(result.stdout)
    fmt = probe.get("format", {})

    duration = float(fmt.get("duration", 0))
    file_size = int(fmt.get("size", 0))

    width = height = None
    codec = None
    fps = None

    for s in probe.get("streams", []):
        if s.get("codec_type") == "video":
            width = s.get("width")
            height = s.get("height")
            codec = s.get("codec_name")
            # fps: avg_frame_rate = "30/1" 형태
            avg_fr = s.get("avg_frame_rate", "0/1")
            if "/" in avg_fr:
                num, den = avg_fr.split("/")
                fps = float(num) / float(den) if float(den) > 0 else None
            break

    meta = VideoMetadata(
        duration=duration,
        width=width,
        height=height,
        codec=codec,
        fps=fps,
        file_size=file_size,
    )
    logger.info(
        "ffprobe_metadata_extracted",
        input_path=input_path,
        duration=duration,
        resolution=f"{width}x{height}" if width else "unknown",
    )
    return meta


def get_duration(input_path: str) -> float:
    """영상 길이(초)만 빠르게 반환한다.

    타임아웃 계산 등 경량 용도에 사용.
    """
    meta = probe_metadata(input_path)
    return meta.duration
