"""Analytics business logic — S12 (F06) + Phase 3 (F18, F20)."""

import csv
import io
import re
import structlog
from collections import defaultdict
from uuid import UUID

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import EngagementHeatmapItem, PerformanceDataResponse

logger = structlog.get_logger()


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    async def get_performance(
        self,
        org_id: UUID,
        platform: str | None = None,
        period: str = "30d",
    ) -> list[PerformanceDataResponse]:
        """Aggregate performance data from publish_results grouped by platform."""
        rows = await self._repo.get_performance_by_platform(org_id, platform=platform)

        performance: list[PerformanceDataResponse] = []
        for row in rows:
            total_views = row.total_views or 0
            total_likes = row.total_likes or 0
            total_shares = row.total_shares or 0
            total_comments = row.total_comments or 0

            # engagement_rate = (likes + shares + comments) / views * 100
            total_interactions = total_likes + total_shares + total_comments
            engagement_rate = (
                round((total_interactions / total_views) * 100, 2)
                if total_views > 0
                else 0.0
            )

            performance.append(
                PerformanceDataResponse(
                    platform=row.platform.value if hasattr(row.platform, "value") else str(row.platform),
                    followers=0,  # Followers require platform API calls; placeholder
                    total_views=total_views,
                    total_likes=total_likes,
                    total_shares=total_shares,
                    total_comments=total_comments,
                    engagement_rate=engagement_rate,
                    period=period,
                )
            )

        logger.info("analytics_performance_fetched", org_id=str(org_id), count=len(performance))
        return performance

    async def get_engagement_heatmap(
        self,
        org_id: UUID,
        period: str = "30d",
    ) -> list[EngagementHeatmapItem]:
        """Build engagement heatmap: hour x day_of_week from publish_results."""
        rows = await self._repo.get_engagement_heatmap(org_id)

        heatmap: list[EngagementHeatmapItem] = []
        for row in rows:
            heatmap.append(
                EngagementHeatmapItem(
                    hour=int(row.hour),
                    day_of_week=int(row.day_of_week),
                    value=float(row.value or 0),
                )
            )

        logger.info("analytics_heatmap_fetched", org_id=str(org_id), count=len(heatmap))
        return heatmap

    async def export_performance(
        self,
        org_id: UUID,
        format: str = "csv",
        period: str = "30d",
    ) -> str:
        """Export performance data as CSV string."""
        data = await self.get_performance(org_id, period=period)
        return self._generate_csv(data)

    @staticmethod
    def _generate_csv(data: list[PerformanceDataResponse]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "플랫폼",
            "팔로워",
            "총 조회수",
            "총 좋아요",
            "총 공유",
            "총 댓글",
            "참여율 (%)",
            "기간",
        ])
        for item in data:
            writer.writerow([
                item.platform,
                item.followers,
                item.total_views,
                item.total_likes,
                item.total_shares,
                item.total_comments,
                item.engagement_rate,
                item.period,
            ])
        return output.getvalue()

    # ── Phase 3 — Sentiment Trend (F18) ──────────────────

    async def get_sentiment_trend(
        self,
        org_id: UUID,
        period: str = "30d",
    ) -> dict:
        """Build sentiment trend data with alerts and keyword cloud."""
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        rows = await self._repo.get_sentiment_trend(org_id, days=days)

        # Build daily trend
        daily: dict[str, dict[str, int]] = defaultdict(
            lambda: {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0, "DANGEROUS": 0}
        )
        for row in rows:
            date_str = str(row.date)
            sentiment_val = row.sentiment.value if hasattr(row.sentiment, "value") else str(row.sentiment)
            daily[date_str][sentiment_val] = row.count

        trend = [
            {
                "date": d,
                "positive": vals.get("POSITIVE", 0),
                "neutral": vals.get("NEUTRAL", 0),
                "negative": vals.get("NEGATIVE", 0),
                "dangerous": vals.get("DANGEROUS", 0),
            }
            for d, vals in sorted(daily.items())
        ]

        # Build keyword cloud from comment bodies
        keyword_rows = await self._repo.get_keyword_frequency(org_id, days=days)
        word_counts: dict[str, dict] = defaultdict(lambda: {"count": 0, "sentiments": defaultdict(int)})

        for row in keyword_rows:
            if not row.body:
                continue
            words = re.findall(r"[가-힣a-zA-Z]{2,}", row.body)
            sentiment_val = row.sentiment.value if hasattr(row.sentiment, "value") else str(row.sentiment)
            for word in words[:20]:
                word_counts[word]["count"] += 1
                word_counts[word]["sentiments"][sentiment_val] += 1

        keyword_cloud = sorted(
            [
                {
                    "keyword": word,
                    "count": data["count"],
                    "sentiment": max(data["sentiments"], key=data["sentiments"].get) if data["sentiments"] else "NEUTRAL",
                    "change": 0.0,
                }
                for word, data in word_counts.items()
                if data["count"] >= 2
            ],
            key=lambda x: x["count"],
            reverse=True,
        )[:50]

        # Generate alerts for high negative sentiment
        alerts = []
        if trend:
            recent = trend[-1]
            total = sum([
                recent.get("positive", 0),
                recent.get("neutral", 0),
                recent.get("negative", 0),
                recent.get("dangerous", 0),
            ])
            if total > 0:
                neg_ratio = (recent.get("negative", 0) + recent.get("dangerous", 0)) / total
                if neg_ratio > 0.2:
                    top_neg_keyword = next(
                        (k["keyword"] for k in keyword_cloud if k["sentiment"] in ("NEGATIVE", "DANGEROUS")),
                        "부정 키워드",
                    )
                    alerts.append({
                        "keyword": top_neg_keyword,
                        "type": "NEGATIVE_SURGE",
                        "change_rate": round(neg_ratio * 100, 1),
                        "risk_level": "HIGH" if neg_ratio > 0.3 else "MEDIUM",
                        "confidence": "MODERATE",
                        "timeframe": "48시간",
                    })

        logger.info("sentiment_trend_fetched", org_id=str(org_id), days=days, trend_count=len(trend))
        return {"alerts": alerts, "sentiment_trend": trend, "keyword_cloud": keyword_cloud}

    # ── Phase 3 — Prediction (F20) ───────────────────────

    async def get_prediction(
        self,
        org_id: UUID,
        content_id: str | None = None,
    ) -> dict:
        """Generate performance prediction from historical data."""
        from uuid import UUID as PyUUID

        pred_data = await self._repo.get_prediction_data(
            org_id, content_id=PyUUID(content_id) if content_id else None,
        )

        data_months = pred_data.get("data_months", 0)
        if data_months < 1:
            return {
                "is_beta": True,
                "content_id": content_id,
                "platform_predictions": [],
                "optimal_publish_times": [],
                "ab_test_suggestions": [],
                "confidence": 0.0,
                "data_months": 0,
            }

        confidence = min(0.95, 0.3 + (data_months * 0.1))
        variance = max(0.2, 1.0 - confidence)

        platform_predictions = []
        for p in pred_data.get("platform_averages", []):
            avg_v = p["avg_views"]
            avg_l = p["avg_likes"]
            platform_predictions.append({
                "platform": p["platform"],
                "estimated_views": {
                    "min": int(avg_v * (1 - variance)),
                    "max": int(avg_v * (1 + variance)),
                } if avg_v > 0 else None,
                "estimated_likes": {
                    "min": int(avg_l * (1 - variance)),
                    "max": int(avg_l * (1 + variance)),
                } if avg_l > 0 else None,
            })

        DOW_NAMES = {0: "SUN", 1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI", 6: "SAT"}
        optimal_times = [
            {
                "day_of_week": DOW_NAMES.get(t["dow"], str(t["dow"])),
                "time_range": f"{int(t['hour']):02d}:00~{int(t['hour'])+1:02d}:00",
                "reason": f"최근 {data_months}개월 평균 참여도 {int(t['avg_engagement'])} 기준",
            }
            for t in pred_data.get("best_times", [])[:3]
        ]

        logger.info("prediction_generated", org_id=str(org_id), confidence=confidence)
        return {
            "is_beta": True,
            "content_id": content_id,
            "platform_predictions": platform_predictions,
            "optimal_publish_times": optimal_times,
            "ab_test_suggestions": [],
            "confidence": round(confidence, 2),
            "data_months": data_months,
        }

    # ── Phase 4 — Benchmark (F23) ───────────────────────

    async def get_benchmark(
        self,
        org_id: UUID,
        period: str = "30d",
    ) -> dict:
        """Generate benchmark analysis comparing org vs industry average."""
        from datetime import datetime, timezone

        period_days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        raw = await self._repo.get_benchmark_data(org_id, period_days=period_days)

        org_data = raw["org_data"]
        all_data = raw["all_data"]

        # Build per-platform industry averages
        platform_orgs: dict[str, list[dict]] = defaultdict(list)
        for row in all_data:
            platform_val = row.platform.value if hasattr(row.platform, "value") else str(row.platform)
            total_views = int(row.total_views or 0)
            total_likes = int(row.total_likes or 0)
            total_shares = int(row.total_shares or 0)
            total_comments = int(row.total_comments or 0)
            post_count = int(row.post_count or 0)
            interactions = total_likes + total_shares + total_comments
            engagement_rate = round((interactions / total_views) * 100, 2) if total_views > 0 else 0.0

            platform_orgs[platform_val].append({
                "org_id": str(row.organization_id),
                "total_views": total_views,
                "total_likes": total_likes,
                "post_count": post_count,
                "engagement_rate": engagement_rate,
            })

        # Build org's own data
        org_by_platform: dict[str, dict] = {}
        for row in org_data:
            platform_val = row.platform.value if hasattr(row.platform, "value") else str(row.platform)
            total_views = int(row.total_views or 0)
            total_likes = int(row.total_likes or 0)
            total_shares = int(row.total_shares or 0)
            total_comments = int(row.total_comments or 0)
            post_count = int(row.post_count or 0)
            interactions = total_likes + total_shares + total_comments
            engagement_rate = round((interactions / total_views) * 100, 2) if total_views > 0 else 0.0

            org_by_platform[platform_val] = {
                "total_views": total_views,
                "total_likes": total_likes,
                "post_count": post_count,
                "engagement_rate": engagement_rate,
            }

        # Build benchmark platforms
        platforms = []
        for platform, orgs in platform_orgs.items():
            org_vals = org_by_platform.get(platform, {})
            total_orgs = len(orgs)

            # Calculate averages
            avg_views = sum(o["total_views"] for o in orgs) / total_orgs if total_orgs > 0 else 0
            avg_likes = sum(o["total_likes"] for o in orgs) / total_orgs if total_orgs > 0 else 0
            avg_posts = sum(o["post_count"] for o in orgs) / total_orgs if total_orgs > 0 else 0
            avg_engagement = sum(o["engagement_rate"] for o in orgs) / total_orgs if total_orgs > 0 else 0

            # Calculate percentile (rank among all orgs)
            org_views = org_vals.get("total_views", 0)
            views_rank = sum(1 for o in orgs if o["total_views"] <= org_views)
            views_percentile = round((views_rank / total_orgs) * 100, 1) if total_orgs > 0 else 0

            org_engagement = org_vals.get("engagement_rate", 0)
            eng_rank = sum(1 for o in orgs if o["engagement_rate"] <= org_engagement)
            eng_percentile = round((eng_rank / total_orgs) * 100, 1) if total_orgs > 0 else 0

            metrics = [
                {
                    "metric": "total_views",
                    "org_value": float(org_views),
                    "industry_average": round(avg_views, 1),
                    "percentile": views_percentile,
                },
                {
                    "metric": "engagement_rate",
                    "org_value": float(org_engagement),
                    "industry_average": round(avg_engagement, 2),
                    "percentile": eng_percentile,
                },
                {
                    "metric": "post_frequency",
                    "org_value": float(org_vals.get("post_count", 0)),
                    "industry_average": round(avg_posts, 1),
                    "percentile": 50.0,
                },
            ]

            # Rank by views
            sorted_orgs = sorted(orgs, key=lambda o: o["total_views"], reverse=True)
            rank = next(
                (i + 1 for i, o in enumerate(sorted_orgs) if o["org_id"] == str(org_id)),
                total_orgs,
            )

            platforms.append({
                "platform": platform,
                "metrics": metrics,
                "rank": rank,
                "total_orgs": total_orgs,
            })

        overall_score = 0.0
        if platforms:
            avg_percentile = sum(
                m["percentile"]
                for p in platforms
                for m in p["metrics"]
            ) / sum(len(p["metrics"]) for p in platforms)
            overall_score = round(avg_percentile, 1)

        logger.info("benchmark_generated", org_id=str(org_id), platform_count=len(platforms))
        return {
            "industry": "공공기관",
            "period": period,
            "platforms": platforms,
            "overall_score": overall_score,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_org_comparison(
        self,
        org_ids: list[UUID],
        period: str = "30d",
    ) -> dict:
        """Compare performance across multiple organizations."""
        period_days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        rows = await self._repo.get_org_comparison_data(org_ids, period_days=period_days)

        organizations = []
        for row in rows:
            total_views = int(row.total_views or 0)
            total_likes = int(row.total_likes or 0)
            total_shares = int(row.total_shares or 0)
            total_comments = int(row.total_comments or 0)
            interactions = total_likes + total_shares + total_comments
            engagement_rate = round((interactions / total_views) * 100, 2) if total_views > 0 else 0.0

            organizations.append({
                "org_id": str(row.organization_id),
                "org_name": row.org_name or "",
                "platform": row.platform.value if hasattr(row.platform, "value") else str(row.platform),
                "followers": 0,
                "total_views": total_views,
                "total_likes": total_likes,
                "engagement_rate": engagement_rate,
                "post_count": int(row.post_count or 0),
            })

        logger.info("org_comparison_generated", org_count=len(org_ids))
        return {"period": period, "organizations": organizations}
