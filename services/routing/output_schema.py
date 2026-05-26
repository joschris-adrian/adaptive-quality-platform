from pydantic import BaseModel


class RoutingMetadata(BaseModel):
    rules_triggered:    list[str]
    heuristic_signals:  dict
    components:         dict
    policy_version:     str
    capacity_available: bool


class RoutedEvent(BaseModel):
    event_id:         str
    action:           str    # auto_action | standard_review | escalated_review | hold
    tier:             str    # automated | standard | expert
    queue:            str    # target Kafka topic
    sla_minutes:      int    # 0 = no SLA (automated), 15 = expert, 60 = standard
    priority:         str
    risk_score:       float
    category:         str
    requires_human:   bool
    routing_metadata: RoutingMetadata