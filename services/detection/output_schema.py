from pydantic import BaseModel
from typing import Optional

class DetectorResult(BaseModel):
    risk_probability: float
    category: str
    detector: str

class ScoredEvent(BaseModel):
    event_id: str
    risk_probability: float   # final aggregated score
    category: str             # winning category
    signals: dict             # raw results from each detector
    source_event: dict        # original raw event