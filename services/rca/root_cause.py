from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict


@dataclass
class FailureRecord:
    event_id:     str
    tier:         str
    category:     str
    failure_type: str        # "false_positive" | "false_negative" | "reversal" | "disagreement"
    risk_score:   float
    signals:      dict
    timestamp:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewer_id:  Optional[str] = None
    metadata:     dict = field(default_factory=dict)


class RCAEngine:
    def __init__(self):
        self._failures:  list[FailureRecord]              = []
        self._clusters:  dict[str, list[FailureRecord]]   = {}
        self._snapshots: list[dict]                       = []

    # ── Ingestion ──────────────────────────────────────────────────────────

    def record_failure(
        self,
        event_id:     str,
        tier:         str,
        category:     str,
        failure_type: str,
        risk_score:   float,
        signals:      dict,
        reviewer_id:  Optional[str] = None,
        metadata:     dict = None,
    ):
        self._failures.append(FailureRecord(
            event_id=event_id, tier=tier, category=category,
            failure_type=failure_type, risk_score=risk_score,
            signals=signals, reviewer_id=reviewer_id,
            metadata=metadata or {},
        ))
        try:
            from services.opensearch.indexer import index_rca_failure
            index_rca_failure({
                "event_id":    event_id,
                "tier":        tier,
                "category":    category,
                "failure_type": failure_type,
                "risk_score":  risk_score,
            })
        except Exception:
            pass

    # ── Failure mode analysis ──────────────────────────────────────────────

    def failure_mode_summary(
        self,
        tier:     Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        records = self._filter(tier=tier, category=category)
        total   = len(records)
        if not total:
            return {"total": 0, "by_failure_type": {}, "by_tier": {}, "by_category": {}}

        by_type     = defaultdict(int)
        by_tier     = defaultdict(int)
        by_category = defaultdict(int)

        for r in records:
            by_type[r.failure_type] += 1
            by_tier[r.tier]         += 1
            by_category[r.category] += 1

        return {
            "total": total,
            "by_failure_type": {
                k: {"count": v, "rate": round(v / total, 4)}
                for k, v in sorted(by_type.items(), key=lambda x: -x[1])
            },
            "by_tier": {
                k: {"count": v, "rate": round(v / total, 4)}
                for k, v in sorted(by_tier.items(), key=lambda x: -x[1])
            },
            "by_category": {
                k: {"count": v, "rate": round(v / total, 4)}
                for k, v in sorted(by_category.items(), key=lambda x: -x[1])
            },
        }

    # ── Signal correlation ─────────────────────────────────────────────────

    def signal_correlation(
        self,
        failure_type: Optional[str] = None,
    ) -> dict:
        """
        For each detector signal, compute the average value across failures
        vs the population average. Signals with a large delta are likely
        contributing factors.
        """
        records = self._filter(failure_type=failure_type)
        if not records:
            return {}

        signal_sums:   defaultdict = defaultdict(float)
        signal_counts: defaultdict = defaultdict(int)

        for r in records:
            for sig, val in r.signals.items():
                if isinstance(val, (int, float)):
                    signal_sums[sig]   += val
                    signal_counts[sig] += 1
                elif isinstance(val, dict):
                    for sub_sig, sub_val in val.items():
                        if isinstance(sub_val, (int, float)):
                            key = f"{sig}.{sub_sig}"
                            signal_sums[key]   += sub_val
                            signal_counts[key] += 1

        return {
            sig: {
                "mean_on_failures": round(signal_sums[sig] / signal_counts[sig], 4),
                "sample_count":     signal_counts[sig],
            }
            for sig in signal_sums
        }

    # ── Reviewer disagreement patterns ────────────────────────────────────

    def disagreement_patterns(self) -> dict:
        disagreements = [r for r in self._failures if r.failure_type == "disagreement"]
        if not disagreements:
            return {"total_disagreements": 0, "by_category": {}, "by_tier": {}, "by_reviewer": {}}

        by_category = defaultdict(int)
        by_tier     = defaultdict(int)
        by_reviewer = defaultdict(int)

        for r in disagreements:
            by_category[r.category] += 1
            by_tier[r.tier]         += 1
            if r.reviewer_id:
                by_reviewer[r.reviewer_id] += 1

        total = len(disagreements)
        return {
            "total_disagreements": total,
            "by_category": {
                k: {"count": v, "rate": round(v / total, 4)}
                for k, v in sorted(by_category.items(), key=lambda x: -x[1])
            },
            "by_tier": {
                k: {"count": v, "rate": round(v / total, 4)}
                for k, v in sorted(by_tier.items(), key=lambda x: -x[1])
            },
            "by_reviewer": {
                k: {"count": v, "rate": round(v / total, 4)}
                for k, v in sorted(by_reviewer.items(), key=lambda x: -x[1])
            },
        }

    # ── Clustering ────────────────────────────────────────────────────────

    def cluster_failures(self, strategy: str = "category_x_type") -> dict:
        """
        Group failures into clusters by a composite key.
        Strategies:
          - category_x_type    : category + failure_type
          - tier_x_type        : tier + failure_type
          - category_x_tier    : category + tier
          - risk_band_x_type   : risk score band + failure_type
        """
        self._clusters = defaultdict(list)

        for r in self._failures:
            key = self._cluster_key(r, strategy)
            self._clusters[key].append(r)

        return {
            cluster_key: {
                "count":        len(records),
                "failure_types": list({r.failure_type for r in records}),
                "categories":   list({r.category     for r in records}),
                "tiers":        list({r.tier          for r in records}),
                "avg_risk_score": round(
                    sum(r.risk_score for r in records) / len(records), 4
                ),
                "sample_event_ids": [r.event_id for r in records[:5]],
            }
            for cluster_key, records in sorted(
                self._clusters.items(), key=lambda x: -len(x[1])
            )
        }

    def _cluster_key(self, record: FailureRecord, strategy: str) -> str:
        band = self._risk_band(record.risk_score)
        return {
            "category_x_type":  f"{record.category}::{record.failure_type}",
            "tier_x_type":      f"{record.tier}::{record.failure_type}",
            "category_x_tier":  f"{record.category}::{record.tier}",
            "risk_band_x_type": f"{band}::{record.failure_type}",
        }.get(strategy, f"{record.category}::{record.failure_type}")

    def _risk_band(self, score: float) -> str:
        if score >= 0.85:   return "critical"
        if score >= 0.65:   return "high"
        if score >= 0.40:   return "medium"
        return "low"

    # ── Drift detection ───────────────────────────────────────────────────

    def failure_rate_trend(self, window_size: int = 50) -> dict:
        """
        Compare failure rates in the first vs most recent window.
        Rising failure rate signals model or policy drift.
        """
        if len(self._failures) < window_size * 2:
            return {
                "status":   "insufficient_data",
                "required": window_size * 2,
                "have":     len(self._failures),
            }

        early  = self._failures[:window_size]
        recent = self._failures[-window_size:]

        def rate_by_type(records):
            counts = defaultdict(int)
            for r in records:
                counts[r.failure_type] += 1
            return {k: round(v / len(records), 4) for k, v in counts.items()}

        early_rates  = rate_by_type(early)
        recent_rates = rate_by_type(recent)
        all_types    = set(early_rates) | set(recent_rates)

        deltas = {
            t: round(recent_rates.get(t, 0) - early_rates.get(t, 0), 4)
            for t in all_types
        }
        drifting = {t: d for t, d in deltas.items() if abs(d) > 0.05}

        return {
            "status":       "drift_detected" if drifting else "stable",
            "early_rates":  early_rates,
            "recent_rates": recent_rates,
            "deltas":       deltas,
            "drifting":     drifting,
            "window_size":  window_size,
        }

    # ── Emerging categories ───────────────────────────────────────────────

    def emerging_categories(self, window_size: int = 50) -> list[dict]:
        """
        Categories that appear in the recent window but were absent or rare
        in the early window — signals new failure patterns.
        """
        if len(self._failures) < window_size * 2:
            return []

        early  = self._failures[:window_size]
        recent = self._failures[-window_size:]

        def category_rates(records):
            counts = defaultdict(int)
            for r in records:
                counts[r.category] += 1
            return {k: v / len(records) for k, v in counts.items()}

        early_rates  = category_rates(early)
        recent_rates = category_rates(recent)
        emerging     = []

        for cat, rate in recent_rates.items():
            early_rate = early_rates.get(cat, 0.0)
            delta      = rate - early_rate
            if delta > 0.05:
                emerging.append({
                    "category":   cat,
                    "early_rate": round(early_rate, 4),
                    "recent_rate": round(rate,      4),
                    "delta":      round(delta,       4),
                })

        return sorted(emerging, key=lambda x: -x["delta"])

    # ── RCA report ────────────────────────────────────────────────────────

    def report(self, window_size: int = 50) -> dict:
        return {
            "generated_at":       datetime.now(timezone.utc).isoformat(),
            "total_failures":     len(self._failures),
            "failure_modes":      self.failure_mode_summary(),
            "signal_correlation": self.signal_correlation(),
            "disagreement":       self.disagreement_patterns(),
            "clusters":           self.cluster_failures(),
            "trend":              self.failure_rate_trend(window_size),
            "emerging_categories": self.emerging_categories(window_size),
        }

    # ── Helpers ───────────────────────────────────────────────────────────

    def _filter(
        self,
        tier:         Optional[str] = None,
        category:     Optional[str] = None,
        failure_type: Optional[str] = None,
    ) -> list[FailureRecord]:
        records = self._failures
        if tier:
            records = [r for r in records if r.tier == tier]
        if category:
            records = [r for r in records if r.category == category]
        if failure_type:
            records = [r for r in records if r.failure_type == failure_type]
        return records