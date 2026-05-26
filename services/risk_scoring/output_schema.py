from pydantic import BaseModel


class RiskComponents(BaseModel):
    likelihood: float
    severity:   float
    exposure:   float


class RiskMetadata(BaseModel):
    rules_triggered:   list[str]
    heuristic_signals: dict
    requires_review:   bool
    auto_actioned:     bool


class RiskScoredEvent(BaseModel):
    event_id:      str
    risk_score:    float       # final normalized score 0–1
    priority:      str         # low | medium | high | critical
    components:    RiskComponents
    category:      str
    risk_metadata: RiskMetadata