"""효과음·배경음악 믹싱 / 오디오 트랙 교체."""

from __future__ import annotations

import os
import subprocess
import time

import structlog

from .common import (
    FFmpegError,
    FFmpegNotInstalledError,
    FFmpegResult,
    calculate_timeout,
    check_ffmpeg_installed,
)
from .probe import get_duration

logger = structlog.get_logger()


def mix_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
    audio_start: float = 0.0,
    video_start: float = 0.0,
    volume: float = 0.3,
    duration: float | None = None,
) -> FFmpegResult:
    """효과음/배경음악을 영상에 믹싱한다.

    원본 영상의 오디오를 유지하면서 추가 오디오를 오버레이한다.

    Args:
        video_path: 원본 영상 파일 경로.
        audio_path: 추가할 오디오 파일 경로.
        output_path: 결과 파일 경로.
        audio_start: 오디오 파일에서 사용할 시작 지점 (초).
        video_start: 영상에서 오디오를 삽입할 시작 지점 (초).
        volume: 추가 오디오의 볼륨 (0.0~1.0).
        duration: 추가 오디오 재생 길이 (초). None이면 전체.

    Returns:
        FFmpegResult.
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotInstalledError("ffmpeg is not installed or not in PATH")

    video_duration = get_duration(video_path)
    timeout = calculate_timeout(video_duration)

    # adelay: 밀리초 단위, 영상 시작 지점에 맞춰 지연
    adelay_ms = int(video_start * 1000)

    # 필터 체인 구성
    filter_parts = [
        f"[1:a]atrim=start={audio_start}",
    ]
    if duration is not None:
        filter_parts[0] += f":duration={duration}"
    filter_parts[0] += f",volume={volume},adelay={adelay_ms}|{adelay_ms}[effect]"
    filter_parts.append("[0:a][effect]amix=inputs=2:duration=first:dropout_transition=2[aout]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path,
    ]

    logger.info(
        "audio_mix_started",
        video_path=video_path,
        audio_path=audio_path,
        volume=volume,
        video_start=video_start,
    )

    start_time = time.monotonic()

    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise FFmpegError(
            f"Audio mix timed out after {timeout}s",
            command=" ".join(cmd),
        ) from e

    elapsed = time.monotonic() - start_time

    if result.returncode != 0 or not os.path.exists(output_path):
        raise FFmpegError(
            "Audio mix failed",
            command=" ".join(cmd),
            stderr=result.stderr.decode(errors="replace")[:500] if result.stderr else "",
        )

    file_size = os.path.getsize(output_path)

    logger.info(
        "audio_mix_completed",
        output_path=output_path,
        processing_time=round(elapsed, 2),
    )

    return FFmpegResult(
        output_path=output_path,
        duration=video_duration,
        file_size=file_size,
        command=" ".join(cmd),
        processing_time=elapsed,
    )


def replace_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> FFmpegResult:
    """영상의 오디오 트랙을 교체한다.

    Args:
        video_path: 원본 영상 파일 경로.
        audio_path: 새 오디오 파일 경로.
        output_path: 결과 파일 경로.

    Returns:
        FFmpegResult.
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotInstalledError("ffmpeg is not installed or not in PATH")

    video_duration = get_duration(video_path)
    timeout = calculate_timeout(video_duration)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    start_time = time.monotonic()

    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise FFmpegError(
            f"Audio replace timed out after {timeout}s",
            command=" ".join(cmd),
        ) from e

    elapsed = time.monotonic() - start_time

    if result.returncode != 0 or not os.path.exists(output_path):
        raise FFmpegError(
            "Audio replace failed",
            command=" ".join(cmd),
            stderr=result.stderr.decode(errors="replace")[:500] if result.stderr else "",
        )

    file_size = os.path.getsize(output_path)

    logger.info(
        "audio_replace_completed",
        output_path=output_path,
        processing_time=round(elapsed, 2),
    )

    return FFmpegResult(
        output_path=output_path,
        duration=video_duration,
        file_size=file_size,
        command=" ".join(cmd),
        processing_time=elapsed,
    )
