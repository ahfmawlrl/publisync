export interface PerformanceData {
  platform: string;
  followers: number;
  total_views: number;
  total_likes: number;
  total_shares: number;
  total_comments: number;
  engagement_rate: number;
  period: string;
}

export interface EngagementHeatmapItem {
  hour: number;
  day_of_week: number;
  value: number;
}

export interface AnalyticsFilters {
  platform?: string;
  period?: string;
}

export interface TrendItem {
  date: string;
  reach: number;
  engagement: number;
}

export interface TopContentItem {
  rank: number;
  content_id: string;
  title: string;
  platform: string;
  metric_label: string;
  metric_value: number;
}

// ── Phase 3 — Sentiment Trend (F18) ──────────────────

export interface SentimentTrendItem {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  dangerous: number;
}

export interface SentimentAlert {
  keyword: string;
  type: string;
  change_rate: number;
  risk_level: string;
  confidence: string;
  timeframe: string;
}

export interface KeywordCloudItem {
  keyword: string;
  count: number;
  sentiment: string;
  change: number;
}

export interface SentimentTrendData {
  alerts: SentimentAlert[];
  sentiment_trend: SentimentTrendItem[];
  keyword_cloud: KeywordCloudItem[];
}

// ── Phase 3 — Prediction (F20) ───────────────────────

export interface PredictionRangeItem {
  min: number;
  max: number;
}

export interface PredictionPlatformItem {
  platform: string;
  estimated_views: PredictionRangeItem | null;
  estimated_likes: PredictionRangeItem | null;
}

export interface OptimalTimeSlot {
  day_of_week: string;
  time_range: string;
  reason: string;
}

export interface AbTestSuggestion {
  field: string;
  option_a: string;
  option_b: string;
  prediction: string;
  reason: string;
}

export interface PredictionData {
  is_beta: boolean;
  content_id: string | null;
  platform_predictions: PredictionPlatformItem[];
  optimal_publish_times: OptimalTimeSlot[];
  ab_test_suggestions: AbTestSuggestion[];
  confidence: number;
  data_months: number;
}

// ── Phase 4 — Benchmark (F23) ───────────────────────

export interface BenchmarkMetric {
  metric: string;
  org_value: number;
  industry_average: number;
  percentile: number;
}

export interface BenchmarkPlatformItem {
  platform: string;
  metrics: BenchmarkMetric[];
  rank: number;
  total_orgs: number;
}

export interface BenchmarkData {
  industry: string;
  period: string;
  platforms: BenchmarkPlatformItem[];
  overall_score: number;
  updated_at: string;
}

export interface OrgComparisonItem {
  org_id: string;
  org_name: string;
  platform: string;
  followers: number;
  total_views: number;
  total_likes: number;
  engagement_rate: number;
  post_count: number;
}

export interface OrgComparisonData {
  period: string;
  organizations: OrgComparisonItem[];
}
