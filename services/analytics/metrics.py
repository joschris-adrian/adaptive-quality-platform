from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict


@dataclass
class DecisionRecord:
    event_id:     str
    tier:         str
    category:     str
    predicted:    str        # "positive" | "negative"
    ground_truth: Optional[str] = None   # set when label arrives
    risk_score:   float = 0.0
    reviewer_id:  Optional[str] = None
    timestamp:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reversed:     bool = False           # True if a later reviewer overturned it
    escalated:    bool = False


class QualityAnalyticsEngine:
    def __init__(self):
        self._records:    list[DecisionRecord]           = []
        self._reversals:  dict[str, bool]                = {}   # event_id → reversed
        self._escalations: dict[str, bool]               = {}
        self._snapshots:  list[dict]                     = []   # periodic snapshots

    # ── Ingestion ──────────────────────────────────────────────────────────

    def record_decision(
        self,
        event_id:    str,
        tier:        str,
        category:    str,
        predicted:   str,
        risk_score:  float = 0.0,
        reviewer_id: Optional[str] = None,
        escalated:   bool = False,
    ):
        record = DecisionRecord(
            event_id=event_id, tier=tier, category=category,
            predicted=predicted, risk_score=risk_score,
            reviewer_id=reviewer_id, escalated=escalated,
        )
        self._records.append(record)
        self._escalations[event_id] = escalated

    def record_ground_truth(self, event_id: str, ground_truth: str):
        for r in self._records:
            if r.event_id == event_id:
                r.ground_truth = ground_truth
                return
        raise KeyError(f"event_id {event_id} not found")

    def record_reversal(self, event_id: str):
        self._reversals[event_id] = True
        for r in self._records:
            if r.event_id == event_id:
                r.reversed = True
                return

    # ── Precision / Recall ─────────────────────────────────────────────────

    def precision_recall(
        self,
        tier:     Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        records = self._filter(tier=tier, category=category, labelled=True)
        tp = sum(1 for r in records if r.predicted == "positive" and r.ground_truth == "positive")
        fp = sum(1 for r in records if r.predicted == "positive" and r.ground_truth == "negative")
        tn = sum(1 for r in records if r.predicted == "negative" and r.ground_truth == "negative")
        fn = sum(1 for r in records if r.predicted == "negative" and r.ground_truth == "positive")

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall    = tp / (tp + fn) if (tp + fn) else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) else 0.0)
        fpr       = fp / (fp + tn) if (fp + tn) else 0.0
        fnr       = fn / (fn + tp) if (fn + tp) else 0.0

        return {
            "precision":           round(precision, 4),
            "recall":              round(recall,    4),
            "f1":                  round(f1,        4),
            "false_positive_rate": round(fpr,       4),
            "false_negative_rate": round(fnr,       4),
            "support":             len(records),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        }

    # ── Escalation metrics ─────────────────────────────────────────────────

    def escalation_rate(
        self,
        tier:     Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        records   = self._filter(tier=tier, category=category)
        total     = len(records)
        escalated = sum(1 for r in records if r.escalated)
        return {
            "total":          total,
            "escalated":      escalated,
            "escalation_rate": round(escalated / total, 4) if total else 0.0,
        }

    # ── Reversal metrics ───────────────────────────────────────────────────

    def reversal_rate(
        self,
        tier:     Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        records  = self._filter(tier=tier, category=category)
        total    = len(records)
        reversed_ = sum(1 for r in records if r.reversed)
        return {
            "total":        total,
            "reversed":     reversed_,
            "reversal_rate": round(reversed_ / total, 4) if total else 0.0,
        }

    # ── Breakdown by tier and category ────────────────────────────────────

    def breakdown_by_tier(self) -> dict:
        tiers = {r.tier for r in self._records}
        return {
            tier: {
                "precision_recall": self.precision_recall(tier=tier),
                "escalation":       self.escalation_rate(tier=tier),
                "reversal":         self.reversal_rate(tier=tier),
            }
            for tier in tiers
        }

    def breakdown_by_category(self) -> dict:
        categories = {r.category for r in self._records}
        return {
            cat: {
                "precision_recall": self.precision_recall(category=cat),
                "escalation":       self.escalation_rate(category=cat),
                "reversal":         self.reversal_rate(category=cat),
            }
            for cat in categories
        }

    # ── Reviewer agreement ─────────────────────────────────────────────────

    def reviewer_agreement(self) -> dict:
        """
        For events seen by multiple reviewers, compute pairwise agreement rate.
        Groups records by event_id and checks if all reviewers agreed.
        """
        by_event: dict[str, list[str]] = defaultdict(list)
        for r in self._records:
            if r.reviewer_id:
                by_event[r.event_id].append(r.predicted)

        multi_reviewed = {
            eid: preds for eid, preds in by_event.items() if len(preds) > 1
        }
        if not multi_reviewed:
            return {"agreement_rate": None, "multi_reviewed_count": 0}

        agreed = sum(
            1 for preds in multi_reviewed.values() if len(set(preds)) == 1
        )
        total  = len(multi_reviewed)
        return {
            "agreement_rate":      round(agreed / total, 4),
            "agreed_count":        agreed,
            "disagreed_count":     total - agreed,
            "multi_reviewed_count": total,
        }

    # ── Drift detection ────────────────────────────────────────────────────

    def drift_report(self, window_size: int = 100) -> dict:
        """
        Compare the first window vs most recent window of labelled records.
        A significant drop in precision or recall signals drift.
        """
        labelled = [r for r in self._records if r.ground_truth is not None]
        if len(labelled) < window_size * 2:
            return {"status": "insufficient_data", "required": window_size * 2, "have": len(labelled)}

        early  = labelled[:window_size]
        recent = labelled[-window_size:]

        def metrics_for(records):
            tp = sum(1 for r in records if r.predicted == "positive" and r.ground_truth == "positive")
            fp = sum(1 for r in records if r.predicted == "positive" and r.ground_truth == "negative")
            fn = sum(1 for r in records if r.predicted == "negative" and r.ground_truth == "positive")
            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall    = tp / (tp + fn) if (tp + fn) else 0.0
            return {"precision": round(precision, 4), "recall": round(recall, 4), "tp": tp, "fp": fp, "fn": fn}

        early_m  = metrics_for(early)
        recent_m = metrics_for(recent)

        precision_delta = recent_m["precision"] - early_m["precision"]
        recall_delta    = recent_m["recall"]    - early_m["recall"]

        return {
            "status":          "drift_detected" if abs(precision_delta) > 0.05 or abs(recall_delta) > 0.05 else "stable",
            "early_window":    early_m,
            "recent_window":   recent_m,
            "precision_delta": round(precision_delta, 4),
            "recall_delta":    round(recall_delta,    4),
            "window_size":     window_size,
        }

    # ── Snapshot (periodic checkpoint) ────────────────────────────────────

    def snapshot(self) -> dict:
        snap = {
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "total_decisions":  len(self._records),
            "labelled_count":   sum(1 for r in self._records if r.ground_truth),
            "global_metrics":   self.precision_recall(),
            "escalation":       self.escalation_rate(),
            "reversal":         self.reversal_rate(),
            "by_tier":          self.breakdown_by_tier(),
            "by_category":      self.breakdown_by_category(),
            "reviewer_agreement": self.reviewer_agreement(),
        }
        self._snapshots.append(snap)
        return snap

    def trend(self, metric: str = "precision") -> list[dict]:
        """Extract a single metric across all snapshots for trend plotting."""
        return [
            {
                "timestamp": s["timestamp"],
                "value":     s["global_metrics"].get(metric),
            }
            for s in self._snapshots
            if s["global_metrics"].get(metric) is not None
        ]

    # ── Helpers ────────────────────────────────────────────────────────────

    def _filter(
        self,
        tier:     Optional[str] = None,
        category: Optional[str] = None,
        labelled: bool = False,
    ) -> list[DecisionRecord]:
        records = self._records
        if tier:
            records = [r for r in records if r.tier == tier]
        if category:
            records = [r for r in records if r.category == category]
        if labelled:
            records = [r for r in records if r.ground_truth is not None]
        return records