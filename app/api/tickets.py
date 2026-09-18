from fastapi import APIRouter
from app.services.data_service import data_service
import numpy as np

router = APIRouter()

@router.get("/tickets")
def get_tickets(limit: int = 50):
    df = data_service.get_data().head(limit)
    return df.replace({np.nan: None}).to_dict(orient="records")
