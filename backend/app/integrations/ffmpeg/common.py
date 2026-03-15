"""ffmpeg 공통 유틸리티 — 데이터클래스, 에러, 진행률 파싱.

모든 ffmpeg 서브모듈이 공유하는 기반 요소를 정의한다.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


# ── 데이터클래스 ──────────────────────────────────────


@dataclass
class VideoMetadata:
    """ffprobe 추출 결과."""

    duration: float = 0.0
    width: int | None = None
    height: int | None = None
    codec: str | None = None
    fps: float | None = None
    file_size: int = 0


@dataclass
class SubtitleSegment:
    """자막 세그먼트 (초 단위)."""

    start: float
    end: float
    text: str


@dataclass
class SubtitleStyle:
    """자막 합성 시 적용할 스타일."""

    font_name: str = "Malgun Gothic"
    font_size: int = 24
    font_color: str = "&HFFFFFF"
    outline_color: str = "&H000000"
    outline_width: int = 2
    margin_v: int = 30
    position: str = "bottom"  # bottom | top | center


@dataclass
class TrimSegment:
    """숏폼 구간 정보."""

    start: float
    end: float
    label: str = ""


@dataclass
class FFmpegResult:
    """ffmpeg 실행 결과."""

    output_path: str
    duration: float = 0.0
    file_size: int = 0
    command: str = ""
    processing_time: float = 0.0


# ── 에러 ──────────────────────────────────────────────


class FFmpegError(Exception):
    """ffmpeg/ffprobe 실행 실패."""

    def __init__(self, message: str, command: str = "", stderr: str = "") -> None:
        self.command = command
        self.stderr = stderr
        super().__init__(message)


class FFmpegNotInstalledError(FFmpegError):
    """시스템에 ffmpeg/ffprobe가 설치되지 않음."""


# ── 유틸리티 함수 ─────────────────────────────────────


def check_ffmpeg_installed() -> bool:
    """ffmpeg 바이너리가 PATH에 있는지 확인."""
    return shutil.which("ffmpeg") is not None


def check_ffprobe_installed() -> bool:
    """ffprobe 바이너리가 PATH에 있는지 확인."""
    return shutil.which("ffprobe") is not None


def calculate_timeout(duration: float) -> int:
    """영상 길이 기반 ffmpeg 처리 타임아웃 계산.

    duration × 3, 최소 60초, 최대 600초.
    """
    timeout = int(duration * 3)
    return max(60, min(timeout, 600))


_PROGRESS_TIME_RE = re.compile(r"out_time_us=(\d+)")


def parse_progress(line: str, total_duration: float) -> float | None:
    """ffmpeg ``-progress pipe:1`` 출력에서 진행률(0.0~1.0) 파싱.

    Args:
        line: ffmpeg progress 출력의 한 줄.
        total_duration: 원본 영상 전체 길이(초).

    Returns:
        0.0~1.0 사이의 진행률, 파싱 불가 시 None.
    """
    if total_duration <= 0:
        return None
    match = _PROGRESS_TIME_RE.search(line)
    if match:
        current_us = int(match.group(1))
        current_seconds = current_us / 1_000_000
        progress = min(current_seconds / total_duration, 1.0)
        return progress
    return None


def seconds_to_srt_time(total_seconds: float) -> str:
    """초를 SRT 시간 형식 ``HH:MM:SS,mmm``으로 변환."""
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    ms = round((total_seconds - int(total_seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
