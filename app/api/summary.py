from fastapi import APIRouter
from app.services.data_service import data_service
from app.schemas import DatasetSummary
import pandas as pd

router = APIRouter()

@router.get("/summary", response_model=DatasetSummary)
def get_summary():
    df = data_service.get_data()
    total = len(df)
    open_tickets = len(df[df["status"] == "Open"])
    escalated = len(df[df["status"] == "Escalated"])
    resolved = len(df[df["status"] == "Resolved"])
    
    avg_rating = df["customer_rating"].mean()
    if pd.isna(avg_rating):
        avg_rating = None
    else:
        avg_rating = round(float(avg_rating), 2)
        
    return DatasetSummary(
        total_tickets=total,
        open_tickets=open_tickets,
        escalated_tickets=escalated,
        resolved_tickets=resolved,
        average_rating=avg_rating
    )
