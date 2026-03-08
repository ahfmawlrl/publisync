"""AI integration module — litellm multi-provider wrapper (Phase 1-B, F02).

Provides async text generation with fallback chain:
  gpt-4o-mini -> claude-sonnet-4-6 -> gemini-1.5-flash -> fallback message.

Usage:
    from app.integrations.ai import generate_text, PROMPTS
    result = await generate_text(prompt="...", system_prompt=PROMPTS["TITLE"])
"""

import time

import structlog

logger = structlog.get_logger()


# ── System prompts per task type ─────────────────────────────

PROMPTS: dict[str, str] = {
    "TITLE": (
        "당신은 공공기관 소셜 미디어 콘텐츠 전문가입니다. "
        "주어진 본문을 기반으로 각 플랫폼에 적합한 제목을 제안합니다. "
        "제목은 간결하고 핵심 메시지를 전달하며, 클릭을 유도해야 합니다. "
        "각 제목은 50자 이내로 작성하고, JSON 배열 형식으로 반환하세요. "
        '예시: [{"content": "제목1", "score": 0.9}, {"content": "제목2", "score": 0.85}]'
    ),
    "DESCRIPTION": (
        "당신은 공공기관 소셜 미디어 콘텐츠 전문가입니다. "
        "주어진 본문을 기반으로 플랫폼에 적합한 설명문(description)을 작성합니다. "
        "공공기관의 톤앤매너를 유지하면서 정보 전달력과 접근성을 높여야 합니다. "
        "JSON 배열 형식으로 반환하세요. "
        '예시: [{"content": "설명문1", "score": 0.88}]'
    ),
    "HASHTAG": (
        "당신은 공공기관 소셜 미디어 해시태그 전문가입니다. "
        "주어진 본문을 기반으로 관련 해시태그를 생성합니다. "
        "해시태그는 '#' 없이 키워드만 반환하세요. "
        "검색 노출과 도달률을 높일 수 있는 해시태그를 우선 배치합니다. "
        "JSON 배열 형식으로 반환하세요. "
        '예시: [{"content": "공공기관", "score": 0.92}, {"content": "정책소식", "score": 0.85}]'
    ),
    "GENERATE_REPLY": (
        "당신은 공공기관 소셜 미디어 댓글 대응 전문가입니다. "
        "주어진 댓글 원문과 콘텐츠 맥락을 기반으로 공손하고 전문적인 답글 초안을 작성합니다. "
        "공공기관의 신뢰성을 유지하면서 시민과의 소통을 강화하는 톤을 사용하세요. "
        "JSON 형식으로 반환하세요. "
        '예시: [{"content": "답글 내용", "score": 0.9, "tone": "formal"}]'
    ),
    "TONE_TRANSFORM": (
        "당신은 공공기관 콘텐츠 톤앤매너 전환 전문가입니다. "
        "주어진 콘텐츠를 지정된 플랫폼과 톤에 맞게 변환합니다. "
        "YouTube는 친근하고 캐주얼한 톤, Instagram은 시각적이고 해시태그 중심, "
        "Facebook은 정보 전달 중심, X는 간결하고 핵심적, 네이버 블로그는 상세하고 SEO 최적화. "
        "JSON 형식으로 반환하세요. "
        '예시: [{"content": "변환된 콘텐츠", "score": 0.88, "platform": "YOUTUBE"}]'
    ),
    "CONTENT_REVIEW": (
        "당신은 공공기관 콘텐츠 표현 가이드 검수 전문가입니다. "
        "주어진 콘텐츠를 검토하여 부적절한 표현, 맞춤법 오류, 민감한 정보 노출, "
        "정치적 편향, 차별적 표현 등을 검출합니다. "
        "각 항목에 대해 심각도(HIGH/MEDIUM/LOW)와 수정 제안을 포함하세요. "
        "JSON 형식으로 반환하세요. "
        '예시: [{"issue": "비속어 사용", "severity": "HIGH", "location": "3번째 문장", '
        '"suggestion": "공식적인 표현으로 변경", "score": 0.95}]'
    ),
    "SUGGEST_EFFECTS": (
        "당신은 소셜 미디어 콘텐츠 효과음 및 이모지 추천 전문가입니다. "
        "주어진 콘텐츠의 분위기와 주제를 분석하여 적합한 이모지와 "
        "영상 편집 시 어울리는 효과음 키워드를 추천합니다. "
        "JSON 형식으로 반환하세요. "
        '예시: [{"type": "emoji", "content": "🎉", "score": 0.9, "context": "축하 관련"}, '
        '{"type": "sound_effect", "content": "celebration_fanfare", "score": 0.85, "context": "성과 발표"}]'
    ),
    "IMPROVE_TEMPLATE": (
        "당신은 공공기관 소셜 미디어 답글 템플릿 개선 전문가입니다. "
        "주어진 기존 답글 템플릿을 분석하고 더 효과적이고 공감적인 버전을 제안합니다. "
        "공공기관의 전문성을 유지하면서 시민 친화적인 톤으로 개선하세요. "
        "JSON 형식으로 반환하세요. "
        '예시: [{"content": "개선된 템플릿", "score": 0.92, "improvements": ["톤 개선", "구체적 안내 추가"]}]'
    ),
    "THUMBNAIL": (
        "당신은 공공기관 소셜 미디어 썸네일 디자인 전문가입니다. "
        "주어진 콘텐츠를 분석하여 효과적인 썸네일 후보를 제안합니다. "
        "각 후보는 레이아웃, 색상 팔레트, 텍스트 오버레이, 시각적 요소를 포함합니다. "
        "JSON 배열 형식으로 반환하세요. "
        '예시: [{"content": "밝은 파란 배경 + 큰 텍스트 제목 + 기관 로고", "score": 0.9, '
        '"layout": "center-text", "colors": ["#1890ff", "#ffffff"], "text_overlay": "2024 정책 안내"}]'
    ),
    "TRANSLATE": (
        "당신은 공공기관 콘텐츠 번역 전문가입니다. "
        "주어진 한국어 콘텐츠를 지정된 언어로 자연스럽게 번역합니다. "
        "공공기관의 전문성과 신뢰성을 유지하면서도 해당 문화권에 맞는 표현을 사용하세요. "
        "반드시 유효한 JSON 형식으로 반환하세요. "
        '예시: {"translated_text": "번역된 텍스트", "target_language": "en", "notes": "추가 설명"}'
    ),
}

# ── Fallback model chain ─────────────────────────────────────

_FALLBACK_MODELS = [
    "gpt-4o-mini",
    "claude-sonnet-4-6",
    "gemini/gemini-1.5-flash",
]

# ── Cost estimation per 1K tokens (approximate) ─────────────

_COST_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "claude-sonnet-4-6": {"prompt": 0.003, "completion": 0.015},
    "gemini/gemini-1.5-flash": {"prompt": 0.000075, "completion": 0.0003},
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD based on token counts."""
    rates = _COST_PER_1K.get(model, {"prompt": 0.001, "completion": 0.002})
    return (prompt_tokens / 1000 * rates["prompt"]) + (
        completion_tokens / 1000 * rates["completion"]
    )


async def generate_text(
    prompt: str,
    system_prompt: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 500,
    temperature: float = 0.7,
) -> dict:
    """Generate text using litellm with automatic fallback chain.

    Returns:
        {
            "content": str,
            "model": str,
            "usage": {
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int,
                "estimated_cost": float,
            },
            "processing_time_ms": int,
            "is_fallback": bool,
        }
    """
    import litellm

    # Build model list: requested model first, then fallbacks (excluding duplicates)
    models_to_try = [model] + [m for m in _FALLBACK_MODELS if m != model]

    start_time = time.monotonic()

    for idx, current_model in enumerate(models_to_try):
        is_fallback = idx > 0
        try:
            response = await litellm.acompletion(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=10,
                num_retries=2,
            )

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            # Parse usage from litellm response
            usage = response.usage  # type: ignore[union-attr]
            prompt_tokens = usage.prompt_tokens or 0
            completion_tokens = usage.completion_tokens or 0
            total_tokens = usage.total_tokens or 0
            content = response.choices[0].message.content or ""  # type: ignore[union-attr]

            logger.info(
                "ai_generate_success",
                model=current_model,
                is_fallback=is_fallback,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                processing_time_ms=elapsed_ms,
            )

            return {
                "content": content,
                "model": current_model,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost": _estimate_cost(
                        current_model, prompt_tokens, completion_tokens
                    ),
                },
                "processing_time_ms": elapsed_ms,
                "is_fallback": is_fallback,
            }

        except Exception as exc:
            logger.warning(
                "ai_generate_fallback",
                model=current_model,
                error=str(exc),
                fallback_index=idx,
            )
            continue

    # All models failed — return fallback response
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    logger.error("ai_generate_all_failed", models_tried=len(models_to_try))

    return {
        "content": "",
        "model": "none",
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
        },
        "processing_time_ms": elapsed_ms,
        "is_fallback": True,
        "error": "All AI providers failed. Please try again or enter content manually.",
    }
