"""영상 구간 절단 (숏폼 렌더링)."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable

import structlog

from .common import (
    FFmpegError,
    FFmpegNotInstalledError,
    FFmpegResult,
    SubtitleStyle,
    calculate_timeout,
    check_ffmpeg_installed,
    parse_progress,
)

logger = structlog.get_logger()


def trim_segment(
    input_path: str,
    output_path: str,
    start: float,
    end: float,
    reencode: bool = True,
    srt_path: str | None = None,
    subtitle_style: SubtitleStyle | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> FFmpegResult:
    """영상의 특정 구간을 절단한다.

    Args:
        input_path: 원본 영상 파일 경로.
        output_path: 절단된 영상 저장 경로.
        start: 시작 시간 (초).
        end: 종료 시간 (초).
        reencode: True면 리인코딩, False면 스트림 복사 (빠르지만 키프레임 불일치 가능).
        srt_path: 자막 파일 경로. 지정 시 절단 구간에 자막도 합성.
        subtitle_style: 자막 스타일 (srt_path 지정 시만 유효).
        on_progress: 진행률 콜백 (0.0~1.0).

    Returns:
        FFmpegResult.

    Raises:
        FFmpegNotInstalledError: ffmpeg 미설치.
        FFmpegError: 절단 실패.
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotInstalledError("ffmpeg is not installed or not in PATH")

    segment_duration = end - start
    if segment_duration <= 0:
        raise FFmpegError(f"Invalid segment: start={start}, end={end}")

    timeout = calculate_timeout(segment_duration)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-to", str(end),
        "-i", input_path,
    ]

    if reencode:
        # 자막 합성 요청 시 vf 필터 추가
        if srt_path and os.path.exists(srt_path):
            from .subtitle import _build_subtitle_filter

            style = subtitle_style or SubtitleStyle()
            vf = _build_subtitle_filter(srt_path, style)
            # -ss로 인한 시간 오프셋 보정: setpts를 사용하지 않아도
            # subtitles 필터는 입력 스트림 기준이므로 자동 보정됨
            cmd.extend(["-vf", vf])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
        ])
    else:
        cmd.extend(["-c", "copy"])

    if on_progress:
        cmd.extend(["-progress", "pipe:1"])

    cmd.append(output_path)

    logger.info(
        "trim_started",
        input_path=input_path,
        start=start,
        end=end,
        reencode=reencode,
        has_subtitles=srt_path is not None,
    )

    start_time = time.monotonic()

    try:
        if on_progress:
            # stderr를 DEVNULL로 보내 파이프 버퍼 데드락 방지
            process = subprocess.Popen(  # noqa: S603
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            assert process.stdout is not None
            for raw_line in process.stdout:
                line = raw_line.decode(errors="replace").strip()
                if "out_time_us=" in line:
                    progress = parse_progress(line, segment_duration)
                    if progress is not None:
                        on_progress(progress)
            process.wait(timeout=timeout)
            returncode = process.returncode
            stderr = ""
        else:
            result = subprocess.run(  # noqa: S603
                cmd, capture_output=True, timeout=timeout,
            )
            returncode = result.returncode
            stderr = result.stderr.decode(errors="replace") if result.stderr else ""
    except subprocess.TimeoutExpired as e:
        raise FFmpegError(
            f"Trim timed out after {timeout}s",
            command=" ".join(cmd),
        ) from e

    elapsed = time.monotonic() - start_time

    if returncode != 0 or not os.path.exists(output_path):
        raise FFmpegError(
            "Trim failed",
            command=" ".join(cmd),
            stderr=stderr[:500],
        )

    file_size = os.path.getsize(output_path)

    logger.info(
        "trim_completed",
        output_path=output_path,
        segment_duration=segment_duration,
        file_size=file_size,
        processing_time=round(elapsed, 2),
    )

    return FFmpegResult(
        output_path=output_path,
        duration=segment_duration,
        file_size=file_size,
        command=" ".join(cmd),
        processing_time=elapsed,
    )
