from fastapi import APIRouter
from app.services.data_service import data_service

router = APIRouter()

@router.get("/health")
def health_check():
    try:
        data = data_service.get_data()
        return {"status": "ok", "dataset_rows": len(data)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
