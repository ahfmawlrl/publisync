"""영상 프레임 추출 (썸네일 생성용)."""

from __future__ import annotations

import os
import subprocess

import structlog

from .common import (
    FFmpegError,
    FFmpegNotInstalledError,
    check_ffmpeg_installed,
)

logger = structlog.get_logger()


def extract_frame(
    input_path: str,
    output_path: str,
    time_offset: float = 3.0,
) -> str:
    """특정 시점의 프레임을 이미지로 추출한다.

    Args:
        input_path: 로컬 영상 파일 경로.
        output_path: 추출 프레임 저장 경로 (e.g. ``/tmp/frame.jpg``).
        time_offset: 추출할 시점 (초).

    Returns:
        output_path (성공 시).

    Raises:
        FFmpegNotInstalledError: ffmpeg 미설치.
        FFmpegError: 프레임 추출 실패.
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotInstalledError("ffmpeg is not installed or not in PATH")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(time_offset),
        "-i", input_path,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ]

    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, timeout=30,
        )
    except subprocess.TimeoutExpired as e:
        raise FFmpegError("Frame extraction timed out", command=" ".join(cmd)) from e

    if result.returncode != 0 or not os.path.exists(output_path):
        raise FFmpegError(
            "Frame extraction failed",
            command=" ".join(cmd),
            stderr=result.stderr.decode(errors="replace")[:500] if result.stderr else "",
        )

    logger.info(
        "frame_extracted",
        input_path=input_path,
        time_offset=time_offset,
        output_path=output_path,
    )
    return output_path


def extract_frames_multi(
    input_path: str,
    output_dir: str,
    timestamps: list[float],
    prefix: str = "frame",
) -> list[str]:
    """여러 시점의 프레임을 일괄 추출한다.

    F16 썸네일 후보 생성에 활용.

    Args:
        input_path: 영상 파일 경로.
        output_dir: 프레임 저장 디렉토리.
        timestamps: 추출할 시점 목록 (초).
        prefix: 출력 파일명 접두사.

    Returns:
        추출된 프레임 파일 경로 목록.
    """
    os.makedirs(output_dir, exist_ok=True)
    results: list[str] = []

    for i, ts in enumerate(timestamps):
        output_path = os.path.join(output_dir, f"{prefix}_{i:03d}.jpg")
        try:
            extract_frame(input_path, output_path, time_offset=ts)
            results.append(output_path)
        except FFmpegError:
            logger.warning("frame_extraction_skipped", timestamp=ts, index=i)

    return results
