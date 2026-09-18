import httpx
import json
import logging
from app.config import settings
from app.schemas import QueryIntent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI Support Ticket Intelligence parser.
Convert the user's natural language question into a strict JSON intent for a support ticket dataset.

Dataset Fields:
- ticket_id: string
- created_at: datetime
- category: "Billing", "Technical", "General"
- priority: "Low", "Medium", "High", "Critical"
- status: "Open", "Resolved", "Escalated"
- response_time_hrs: float
- resolution_time_hrs: float (null if unresolved)
- agent_id: string
- customer_rating: int 1-5
- issue_summary: string

Allowed operations: "count", "average", "sum", "min", "max", "list", "group_count", "group_average", "top", "bottom"
Time periods: "today", "week", "month"

Semantics:
- "unresolved" -> status IN ["Open", "Escalated"]
- "open" -> status = "Open"
- "resolved" -> status = "Resolved"
- "critical" -> priority = "Critical"
- "high priority" -> priority = "High"

Examples:
"How many critical tickets are unresolved?"
{"operation": "count", "filters": {"priority": "Critical", "status": "unresolved"}}

"Which agent resolved the most tickets this month?"
{"operation": "top", "metric": "ticket_count", "group_by": "agent_id", "filters": {"status": "Resolved"}, "time_period": "month", "limit": 1}

"Show me all Critical tickets not resolved within 12 hours"
{"operation": "list", "filters": {"priority": "Critical", "not_resolved_within_hrs": 12}}

Return ONLY valid JSON. No markdown formatting, no explanations.
"""

class LLMService:
    def __init__(self):
        self.url = f"{settings.ollama_url}/api/generate"
        self.model = settings.ollama_model

    def parse_query_fallback(self, query: str) -> dict:
        """Fallback deterministic parser when Ollama is unavailable."""
        query = query.lower()
        intent = {"operation": "list", "filters": {}}
        
        if "how many" in query or "count" in query:
            intent["operation"] = "count"
        elif "average" in query:
            intent["operation"] = "average"
            if "rating" in query:
                intent["metric"] = "customer_rating"
            elif "resolution" in query:
                intent["metric"] = "resolution_time_hrs"
                
        if "top" in query or "most" in query:
            intent["operation"] = "top"
            intent["limit"] = 1
            if "agent" in query:
                intent["group_by"] = "agent_id"
            if "resolved" in query:
                intent["filters"]["status"] = "Resolved"
                
        if "lowest" in query or "bottom" in query:
            intent["operation"] = "bottom"
            intent["limit"] = 1
            if "agent" in query:
                intent["group_by"] = "agent_id"
            if "rating" in query:
                intent["metric"] = "customer_rating"

        # Filters
        if "unresolved" in query or "not resolved" in query:
            intent["filters"]["status"] = "unresolved"
        elif "open" in query:
            intent["filters"]["status"] = "Open"
        elif "resolved" in query:
            intent["filters"]["status"] = "Resolved"
            
        if "critical" in query:
            intent["filters"]["priority"] = "Critical"
        elif "high priority" in query:
            intent["filters"]["priority"] = "High"
            
        if "technical" in query:
            intent["filters"]["category"] = "Technical"
        elif "billing" in query:
            intent["filters"]["category"] = "Billing"
            
        if "this month" in query:
            intent["time_period"] = "month"
        elif "this week" in query:
            intent["time_period"] = "week"
            
        if "within 12 hours" in query or "greater than 12" in query:
             intent["filters"]["not_resolved_within_hrs"] = 12
        if "above 20 hours" in query:
             intent["filters"]["resolution_time_greater_than"] = 20
            
        if intent["operation"] == "average" and "agent" in query:
            intent["operation"] = "group_average"
            intent["group_by"] = "agent_id"
            
        return intent

    async def get_intent(self, query: str) -> tuple[dict, bool]:
        """Returns (intent_dict, llm_used_boolean)"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "model": self.model,
                    "prompt": f"{SYSTEM_PROMPT}\nUser Query: {query}\nJSON:",
                    "stream": False,
                    "format": "json"
                }
                response = await client.post(self.url, json=payload)
                response.raise_for_status()
                data = response.json()
                response_text = data.get("response", "")
                
                try:
                    intent_dict = json.loads(response_text)
                    return intent_dict, True
                except json.JSONDecodeError:
                    logger.warning("LLM returned invalid JSON, using fallback.")
                    return self.parse_query_fallback(query), False
        except Exception as e:
            logger.warning(f"Ollama unavailable or failed ({str(e)}), using fallback.")
            return self.parse_query_fallback(query), False

llm_service = LLMService()
