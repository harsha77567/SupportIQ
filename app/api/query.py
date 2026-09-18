from fastapi import APIRouter, HTTPException
from app.schemas import QueryRequest, QueryResponse
from app.services.llm_service import llm_service
from app.analytics.query_engine import query_engine

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    intent_dict, llm_used = await llm_service.get_intent(request.query)
    
    try:
        answer, data = query_engine.execute(intent_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")
        
    return QueryResponse(
        question=request.query,
        intent=intent_dict,
        answer=answer,
        data=data,
        llm_used=llm_used
    )
