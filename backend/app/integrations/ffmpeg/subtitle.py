"""자막 SRT 파일 생성 + 자막 합성 (burn-in)."""

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
    SubtitleSegment,
    SubtitleStyle,
    calculate_timeout,
    check_ffmpeg_installed,
    seconds_to_srt_time,
)
from .probe import get_duration

logger = structlog.get_logger()


def generate_srt(segments: list[SubtitleSegment], output_path: str) -> str:
    """자막 세그먼트 목록을 SRT 파일로 생성한다.

    Args:
        segments: 자막 세그먼트 리스트.
        output_path: SRT 파일 저장 경로.

    Returns:
        output_path.
    """
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        start_str = seconds_to_srt_time(seg.start)
        end_str = seconds_to_srt_time(seg.end)
        lines.append(f"{i}")
        lines.append(f"{start_str} --> {end_str}")
        lines.append(seg.text)
        lines.append("")  # 빈 줄 구분

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("srt_file_generated", output_path=output_path, segment_count=len(segments))
    return output_path


def _build_subtitle_filter(srt_path: str, style: SubtitleStyle) -> str:
    """ffmpeg subtitles 필터 문자열을 생성한다."""
    # Windows 경로의 백슬래시와 콜론을 ffmpeg 필터 구문에 맞게 이스케이프
    escaped_path = srt_path.replace("\\", "/").replace(":", "\\:")

    # MarginV 값 계산 (position에 따라)
    margin_v = style.margin_v
    if style.position == "top":
        margin_v = 20  # 상단 고정
    elif style.position == "center":
        margin_v = 0  # 중앙

    # Alignment: bottom=2, top=6, center=10 (ASS 기준)
    alignment = {"bottom": 2, "top": 6, "center": 10}.get(style.position, 2)

    force_style = (
        f"FontName={style.font_name},"
        f"FontSize={style.font_size},"
        f"PrimaryColour={style.font_color},"
        f"OutlineColour={style.outline_color},"
        f"Outline={style.outline_width},"
        f"MarginV={margin_v},"
        f"Alignment={alignment}"
    )

    return f"subtitles='{escaped_path}':force_style='{force_style}'"


def burn_subtitles(
    input_path: str,
    output_path: str,
    srt_path: str,
    style: SubtitleStyle | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> FFmpegResult:
    """SRT 자막을 영상에 합성(burn-in)한다.

    Args:
        input_path: 원본 영상 파일 경로.
        output_path: 자막 합성된 영상 저장 경로.
        srt_path: SRT 자막 파일 경로.
        style: 자막 스타일. None이면 기본값 사용.
        on_progress: 진행률 콜백 (0.0~1.0).

    Returns:
        FFmpegResult.

    Raises:
        FFmpegNotInstalledError: ffmpeg 미설치.
        FFmpegError: 합성 실패.
    """
    if not check_ffmpeg_installed():
        raise FFmpegNotInstalledError("ffmpeg is not installed or not in PATH")

    if style is None:
        style = SubtitleStyle()

    duration = get_duration(input_path)
    timeout = calculate_timeout(duration)

    vf = _build_subtitle_filter(srt_path, style)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
    ]

    # 진행률 콜백이 있으면 -progress 옵션 추가
    if on_progress:
        cmd.extend(["-progress", "pipe:1"])

    cmd.append(output_path)

    logger.info(
        "subtitle_burnin_started",
        input_path=input_path,
        srt_path=srt_path,
        style=style.__dict__,
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
                    from .common import parse_progress

                    progress = parse_progress(line, duration)
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
            f"Subtitle burn-in timed out after {timeout}s",
            command=" ".join(cmd),
        ) from e

    elapsed = time.monotonic() - start_time

    if returncode != 0 or not os.path.exists(output_path):
        raise FFmpegError(
            "Subtitle burn-in failed",
            command=" ".join(cmd),
            stderr=stderr[:500],
        )

    file_size = os.path.getsize(output_path)

    logger.info(
        "subtitle_burnin_completed",
        output_path=output_path,
        file_size=file_size,
        processing_time=round(elapsed, 2),
    )

    return FFmpegResult(
        output_path=output_path,
        duration=duration,
        file_size=file_size,
        command=" ".join(cmd),
        processing_time=elapsed,
    )
