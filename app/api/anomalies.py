from fastapi import APIRouter, Query
from app.schemas import AnomaliesResponse
from app.analytics.anomaly_detector import anomaly_detector

router = APIRouter()

@router.get("/anomalies", response_model=AnomaliesResponse)
def get_anomalies(threshold_hours: float = Query(24.0, description="Age threshold in hours for high priority tickets")):
    return anomaly_detector.detect_anomalies(threshold_hours)
