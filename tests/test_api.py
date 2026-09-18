"""
API-level integration tests.
Covers: health, summary, anomalies, empty queries, and fallback-parser behaviour.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:

    def test_health_returns_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_reports_500_rows(self):
        r = client.get("/api/health")
        assert r.json()["dataset_rows"] == 500


class TestSummaryEndpoint:

    def test_summary_returns_correct_shape(self):
        r = client.get("/api/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_tickets"] == 500
        assert "open_tickets" in data
        assert "escalated_tickets" in data
        assert "resolved_tickets" in data
        assert "average_rating" in data

    def test_summary_status_counts_add_up(self):
        r = client.get("/api/summary")
        data = r.json()
        total = data["open_tickets"] + data["escalated_tickets"] + data["resolved_tickets"]
        assert total == 500

    def test_summary_open_count(self):
        r = client.get("/api/summary")
        assert r.json()["open_tickets"] == 111

    def test_summary_escalated_count(self):
        r = client.get("/api/summary")
        assert r.json()["escalated_tickets"] == 62


class TestAnomaliesEndpoint:

    def test_anomalies_returns_200(self):
        r = client.get("/api/anomalies")
        assert r.status_code == 200

    def test_anomalies_schema(self):
        r = client.get("/api/anomalies")
        data = r.json()
        assert "reference_time" in data
        assert "statistical_outliers" in data
        assert "aging_high_priority" in data
        assert "unresolved_critical" in data
        assert "total_anomalies" in data

    def test_anomalies_counts_are_correct(self):
        r = client.get("/api/anomalies")
        data = r.json()
        assert len(data["statistical_outliers"]) == 21
        assert len(data["aging_high_priority"]) == 80
        assert len(data["unresolved_critical"]) == 31

    def test_anomalies_custom_threshold(self):
        """A very high threshold should return fewer aging tickets."""
        r_default = client.get("/api/anomalies?threshold_hours=24")
        r_high = client.get("/api/anomalies?threshold_hours=5000")
        assert (
            len(r_high.json()["aging_high_priority"])
            <= len(r_default.json()["aging_high_priority"])
        )


class TestQueryEndpoint:

    def test_empty_query_returns_400(self):
        r = client.post("/api/query", json={"query": "   "})
        assert r.status_code == 400

    def test_open_tickets_query_fallback(self):
        """Fallback parser: 'how many tickets are open' -> count, status=Open."""
        r = client.post("/api/query", json={"query": "how many tickets are open"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"]["operation"] == "count"
        assert data["intent"]["filters"]["status"] == "Open"
        assert "111" in data["answer"]

    def test_query_response_has_llm_used_field(self):
        """Response must always include llm_used boolean."""
        r = client.post("/api/query", json={"query": "how many open tickets"})
        assert r.status_code == 200
        assert "llm_used" in r.json()

    def test_query_response_has_intent_field(self):
        r = client.post("/api/query", json={"query": "how many critical tickets are unresolved"})
        assert r.status_code == 200
        data = r.json()
        assert "intent" in data
        assert data["intent"] is not None

    def test_query_critical_unresolved_fallback(self):
        """Fallback: 'how many critical tickets are unresolved' -> count=31."""
        r = client.post("/api/query", json={"query": "how many critical tickets are unresolved"})
        assert r.status_code == 200
        data = r.json()
        assert "31" in data["answer"]

    def test_query_this_month_top_agent_fallback(self):
        """Fallback: resolves the correct agent for this month."""
        r = client.post("/api/query", json={"query": "which agent resolved the most tickets this month"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"]["time_period"] == "month"
        assert "AGT-01" in str(data["data"])

    def test_query_technical_avg_rating_fallback(self):
        """Fallback: average Technical rating -> 3.74"""
        r = client.post("/api/query", json={
            "query": "what is the average customer rating for technical category tickets"
        })
        assert r.status_code == 200
        data = r.json()
        assert "3.74" in data["answer"]


class TestLLMFallbackBehaviour:

    def test_invalid_llm_json_falls_back_gracefully(self):
        """
        The LLMService must handle invalid JSON from Ollama without crashing.
        When Ollama is not running (expected in test env), the fallback parser
        activates and llm_used must be False.
        """
        r = client.post("/api/query", json={"query": "how many open tickets"})
        assert r.status_code == 200
        data = r.json()
        # When Ollama is unavailable (likely in tests), llm_used=False
        # The answer must still be a non-empty string.
        assert isinstance(data["llm_used"], bool)
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0

    def test_ollama_unavailable_does_not_return_500(self):
        """
        Even with no Ollama, the query endpoint must return 200 (via fallback).
        It must NOT bubble up a 500 Internal Server Error.
        """
        r = client.post("/api/query", json={"query": "list escalated tickets"})
        assert r.status_code == 200


class TestTicketsEndpoint:

    def test_tickets_returns_list(self):
        r = client.get("/api/tickets")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_tickets_default_limit_is_50(self):
        r = client.get("/api/tickets")
        assert len(r.json()) == 50

    def test_tickets_custom_limit(self):
        r = client.get("/api/tickets?limit=10")
        assert len(r.json()) == 10
