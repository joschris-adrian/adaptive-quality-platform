from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QualityMetrics:
    true_positives:  int = 0
    false_positives: int = 0
    true_negatives:  int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0

    @property
    def f1(self) -> float:
        denom = self.precision + self.recall
        return 2 * self.precision * self.recall / denom if denom else 0.0

    @property
    def false_positive_rate(self) -> float:
        denom = self.false_positives + self.true_negatives
        return self.false_positives / denom if denom else 0.0

    @property
    def false_negative_rate(self) -> float:
        denom = self.false_negatives + self.true_positives
        return self.false_negatives / denom if denom else 0.0

    @property
    def accuracy(self) -> float:
        total = (self.true_positives + self.false_positives +
                 self.true_negatives + self.false_negatives)
        correct = self.true_positives + self.true_negatives
        return correct / total if total else 0.0

    def to_dict(self) -> dict:
        return {
            "precision":          round(self.precision, 4),
            "recall":             round(self.recall, 4),
            "f1":                 round(self.f1, 4),
            "accuracy":           round(self.accuracy, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "true_positives":     self.true_positives,
            "false_positives":    self.false_positives,
            "true_negatives":     self.true_negatives,
            "false_negatives":    self.false_negatives,
        }


class QualityTracker:
    """
    Accumulates decision outcomes and computes quality metrics per tier
    and per category.
    """

    def __init__(self):
        self._global: QualityMetrics                   = QualityMetrics()
        self._by_tier: dict[str, QualityMetrics]       = {}
        self._by_category: dict[str, QualityMetrics]   = {}

    def record(
        self,
        tier:         str,
        category:     str,
        predicted:    str,   # "positive" | "negative"
        ground_truth: str,   # "positive" | "negative"
    ):
        tp = predicted == "positive" and ground_truth == "positive"
        fp = predicted == "positive" and ground_truth == "negative"
        tn = predicted == "negative" and ground_truth == "negative"
        fn = predicted == "negative" and ground_truth == "positive"

        for bucket in [
            self._global,
            self._get_or_create(self._by_tier,     tier),
            self._get_or_create(self._by_category, category),
        ]:
            bucket.true_positives  += int(tp)
            bucket.false_positives += int(fp)
            bucket.true_negatives  += int(tn)
            bucket.false_negatives += int(fn)

    def _get_or_create(self, store: dict, key: str) -> QualityMetrics:
        if key not in store:
            store[key] = QualityMetrics()
        return store[key]

    def report(self) -> dict:
        return {
            "global":      self._global.to_dict(),
            "by_tier":     {k: v.to_dict() for k, v in self._by_tier.items()},
            "by_category": {k: v.to_dict() for k, v in self._by_category.items()},
        }