from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict, Union

class QueryRequest(BaseModel):
    query: str

class QueryIntent(BaseModel):
    operation: str # count, average, sum, min, max, list, group_count, group_average, top, bottom
    filters: Optional[Dict[str, Any]] = None
    group_by: Optional[str] = None
    metric: Optional[str] = None
    time_period: Optional[str] = None # today, week, month
    limit: Optional[int] = None

class QueryResponse(BaseModel):
    question: str
    intent: Optional[Dict[str, Any]] = None
    answer: str
    data: List[Dict[str, Any]] = []
    llm_used: bool = False

class TicketAnomaly(BaseModel):
    ticket_id: str
    priority: str
    category: str
    agent_id: Optional[str] = None
    created_at: str
    issue_summary: Optional[str] = None
    anomaly_reason: str
    resolution_time_hrs: Optional[float] = None
    age_hours: Optional[float] = None
    status: str

class AnomaliesResponse(BaseModel):
    reference_time: str
    resolution_time_upper_bound_hrs: Optional[float] = None
    statistical_outliers: List[TicketAnomaly] = []
    aging_high_priority: List[TicketAnomaly] = []
    unresolved_critical: List[TicketAnomaly] = []
    total_anomalies: int

class DatasetSummary(BaseModel):
    total_tickets: int
    open_tickets: int
    escalated_tickets: int
    resolved_tickets: int
    average_rating: Optional[float] = None
