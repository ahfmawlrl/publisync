"""Pydantic schemas for Analytics endpoints — S12 (F06)."""

from pydantic import BaseModel


class PerformanceDataResponse(BaseModel):
    platform: str
    followers: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_shares: int = 0
    total_comments: int = 0
    engagement_rate: float = 0.0
    period: str


class EngagementHeatmapItem(BaseModel):
    hour: int
    day_of_week: int
    value: float


class TrendItem(BaseModel):
    date: str
    reach: int = 0
    engagement: int = 0


class TopContentItem(BaseModel):
    rank: int
    content_id: str
    title: str
    platform: str
    metric_label: str  # e.g. "12.3K 조회"
    metric_value: int = 0


class ExportResponse(BaseModel):
    download_url: str
    filename: str


# ── Phase 3 — Sentiment Trend (F18) ──────────────────


class SentimentTrendItem(BaseModel):
    date: str
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    dangerous: int = 0


class SentimentAlert(BaseModel):
    keyword: str
    type: str  # NEGATIVE_SURGE, POSITIVE_SURGE
    change_rate: float = 0.0
    risk_level: str = "LOW"
    confidence: str = "LOW"
    timeframe: str = "48시간"


class KeywordCloudItem(BaseModel):
    keyword: str
    count: int = 0
    sentiment: str = "NEUTRAL"
    change: float = 0.0


class SentimentTrendResponse(BaseModel):
    alerts: list[SentimentAlert] = []
    sentiment_trend: list[SentimentTrendItem] = []
    keyword_cloud: list[KeywordCloudItem] = []


# ── Phase 3 — Prediction (F20) ───────────────────────


class PredictionRangeItem(BaseModel):
    min: int = 0
    max: int = 0


class PredictionPlatformItem(BaseModel):
    platform: str
    estimated_views: PredictionRangeItem | None = None
    estimated_likes: PredictionRangeItem | None = None


class OptimalTimeSlot(BaseModel):
    day_of_week: str
    time_range: str
    reason: str = ""


class AbTestSuggestion(BaseModel):
    field: str
    option_a: str
    option_b: str
    prediction: str
    reason: str = ""


class PredictionResponse(BaseModel):
    is_beta: bool = True
    content_id: str | None = None
    platform_predictions: list[PredictionPlatformItem] = []
    optimal_publish_times: list[OptimalTimeSlot] = []
    ab_test_suggestions: list[AbTestSuggestion] = []
    confidence: float = 0.0
    data_months: int = 0


# ── Phase 4 — Benchmark (F23) ───────────────────────


class BenchmarkMetric(BaseModel):
    metric: str  # followers, engagement_rate, post_frequency, avg_views
    org_value: float = 0.0
    industry_average: float = 0.0
    percentile: float = 0.0  # 0-100


class BenchmarkPlatformItem(BaseModel):
    platform: str
    metrics: list[BenchmarkMetric] = []
    rank: int = 0
    total_orgs: int = 0


class BenchmarkResponse(BaseModel):
    industry: str = ""
    period: str = "30d"
    platforms: list[BenchmarkPlatformItem] = []
    overall_score: float = 0.0
    updated_at: str = ""


class OrgComparisonItem(BaseModel):
    org_id: str
    org_name: str
    platform: str
    followers: int = 0
    total_views: int = 0
    total_likes: int = 0
    engagement_rate: float = 0.0
    post_count: int = 0


class OrgComparisonResponse(BaseModel):
    period: str = "30d"
    organizations: list[OrgComparisonItem] = []
