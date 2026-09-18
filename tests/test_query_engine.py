"""
Comprehensive unit tests for the deterministic QueryEngine.

All expected values are pre-verified against the real 500-row CSV:
  reference_time = 2024-03-30 18:06:00 (max created_at in dataset)
"""
import pytest
import pandas as pd
import math
from app.services.data_service import data_service
from app.analytics.query_engine import query_engine


@pytest.fixture(autouse=True, scope="module")
def load_data():
    data_service.load_data()


class TestCountOperations:

    def test_open_ticket_count(self):
        """Open tickets -> 111"""
        _, data = query_engine.execute({"operation": "count", "filters": {"status": "Open"}})
        assert data[0]["count"] == 111

    def test_escalated_ticket_count(self):
        """Escalated tickets -> 62"""
        _, data = query_engine.execute({"operation": "count", "filters": {"status": "Escalated"}})
        assert data[0]["count"] == 62

    def test_total_ticket_count_no_filters(self):
        """No filters -> all 500 tickets."""
        _, data = query_engine.execute({"operation": "count"})
        assert data[0]["count"] == 500

    def test_critical_unresolved_count(self):
        """
        'unresolved' means status IN [Open, Escalated].
        Critical + unresolved -> 31
        """
        _, data = query_engine.execute({
            "operation": "count",
            "filters": {"priority": "Critical", "status": "unresolved"}
        })
        assert data[0]["count"] == 31

    def test_resolved_this_month(self):
        """Resolved tickets in March 2024 (reference month) -> 121"""
        _, data = query_engine.execute({
            "operation": "count",
            "filters": {"status": "Resolved"},
            "time_period": "month"
        })
        assert data[0]["count"] == 121

    def test_resolution_above_20h_count(self):
        """Resolved tickets with resolution_time_hrs > 20 -> 106"""
        _, data = query_engine.execute({
            "operation": "count",
            "filters": {"resolution_time_greater_than": 20}
        })
        assert data[0]["count"] == 106

    def test_tickets_this_week_count(self):
        """7-day window ending at reference_time -> 55"""
        _, data = query_engine.execute({"operation": "count", "time_period": "week"})
        assert data[0]["count"] == 55


class TestAverageOperations:

    def test_average_technical_rating(self):
        """Average customer_rating for Technical -> 3.74"""
        answer, data = query_engine.execute({
            "operation": "average",
            "metric": "customer_rating",
            "filters": {"category": "Technical"}
        })
        assert abs(data[0]["customer_rating"] - 3.74) < 0.01
        assert "3.74" in answer

    def test_average_billing_resolution_time(self):
        """Average resolution_time_hrs for Billing -> ~16.33"""
        _, data = query_engine.execute({
            "operation": "average",
            "metric": "resolution_time_hrs",
            "filters": {"category": "Billing"}
        })
        assert abs(data[0]["resolution_time_hrs"] - 16.33) < 0.1

    def test_average_invalid_metric_does_not_crash(self):
        """Invalid metric returns error message, not exception."""
        answer, _ = query_engine.execute({"operation": "average", "metric": "nonexistent_column"})
        assert "invalid" in answer.lower() or "missing" in answer.lower()


class TestTopBottomOperations:

    def test_top_resolving_agent_all_time(self):
        """Most resolved tickets all-time -> AGT-09 (37)"""
        _, data = query_engine.execute({
            "operation": "top",
            "metric": "ticket_count",
            "group_by": "agent_id",
            "filters": {"status": "Resolved"},
            "limit": 1
        })
        assert data[0]["agent_id"] == "AGT-09"
        assert data[0]["count"] == 37

    def test_top_resolving_agent_this_month(self):
        """Most resolved tickets in March 2024 -> AGT-01 (16)"""
        _, data = query_engine.execute({
            "operation": "top",
            "metric": "ticket_count",
            "group_by": "agent_id",
            "filters": {"status": "Resolved"},
            "time_period": "month",
            "limit": 1
        })
        assert data[0]["agent_id"] == "AGT-01"
        assert data[0]["count"] == 16

    def test_bottom_agent_by_avg_rating(self):
        """Lowest average customer rating -> AGT-08 (~3.48)"""
        _, data = query_engine.execute({
            "operation": "bottom",
            "metric": "customer_rating",
            "group_by": "agent_id",
            "limit": 1
        })
        assert data[0]["agent_id"] == "AGT-08"
        assert abs(data[0]["customer_rating"] - 3.48) < 0.01

    def test_top_missing_groupby_returns_error(self):
        """Top with no group_by must return graceful error, not crash."""
        answer, data = query_engine.execute({"operation": "top", "limit": 1})
        assert "missing" in answer.lower() or data == []


class TestListOperations:

    def test_list_unresolved_critical_status_filter(self):
        """List unresolved critical -> 31 rows."""
        _, data = query_engine.execute({
            "operation": "list",
            "filters": {"priority": "Critical", "status": "unresolved"}
        })
        assert len(data) == 31
        for row in data:
            assert row["priority"] == "Critical"
            assert row["status"] in ("Open", "Escalated")

    def test_critical_not_resolved_within_12h_correct_null_handling(self):
        """
        'Show me all Critical tickets not resolved within 12 hours.'

        KEY SEMANTIC: resolution_time_hrs is NULL for unresolved tickets.
        A naive resolution_time_hrs > 12 silently drops all unresolved rows.

        Correct logic (not_resolved_within_hrs filter):
          - Resolved, but took > 12 hours
          - Unresolved, and age from reference_time > 12 hours

        Expected: 34 tickets.
        """
        _, data = query_engine.execute({
            "operation": "list",
            "filters": {"priority": "Critical", "not_resolved_within_hrs": 12}
        })
        assert len(data) == 34, (
            f"Expected 34 critical tickets not resolved within 12h, got {len(data)}. "
            "Ensure unresolved NULLs are compared by age, not resolution_time_hrs."
        )
        for row in data:
            assert row["priority"] == "Critical"

    def test_naive_null_filter_gives_fewer_results(self):
        """
        Prove the naive approach (resolution_time_greater_than) gives fewer
        results, confirming the null-aware filter is necessary.
        """
        _, naive = query_engine.execute({
            "operation": "count",
            "filters": {"priority": "Critical", "resolution_time_greater_than": 12}
        })
        _, correct = query_engine.execute({
            "operation": "count",
            "filters": {"priority": "Critical", "not_resolved_within_hrs": 12}
        })
        assert correct[0]["count"] > naive[0]["count"]

    def test_list_returns_all_10_columns(self):
        """List preserves all original CSV columns."""
        _, data = query_engine.execute({
            "operation": "list",
            "filters": {"status": "Open"},
            "limit": 1
        })
        expected_cols = {
            "ticket_id", "created_at", "category", "priority", "status",
            "response_time_hrs", "resolution_time_hrs", "agent_id",
            "customer_rating", "issue_summary"
        }
        assert expected_cols.issubset(set(data[0].keys()))

    def test_null_values_serialised_as_empty_string_not_nan(self):
        """NaN values must be '' for JSON safety - not float NaN."""
        _, data = query_engine.execute({
            "operation": "list",
            "filters": {"status": "Open"},
            "limit": 10
        })
        for row in data:
            val = row["resolution_time_hrs"]
            if val != "":
                assert not (isinstance(val, float) and math.isnan(val)), (
                    "NaN resolution_time_hrs must be serialised as empty string, not float NaN"
                )

    def test_list_impossible_filter_returns_empty_gracefully(self):
        """Impossible filter returns [] without crashing."""
        _, data = query_engine.execute({
            "operation": "list",
            "filters": {"status": "Resolved"},
            "time_period": "today"
        })
        assert isinstance(data, list)


class TestTimePeriodSemantics:

    def test_month_uses_dataset_reference_time_not_system_clock(self):
        """
        'This month' must use reference_time=2024-03-30, not the system clock.
        If the system clock were used, the count would be 0 (CSV is from 2024).
        """
        _, data = query_engine.execute({"operation": "count", "time_period": "month"})
        df = data_service.get_data()
        ref = data_service.reference_time
        expected = len(df[
            (df["created_at"].dt.year == ref.year) &
            (df["created_at"].dt.month == ref.month)
        ])
        assert data[0]["count"] == expected
        assert data[0]["count"] > 0, "Month filter returned 0 - likely using system clock instead of reference_time"

    def test_week_is_7_day_window_ending_at_reference_time(self):
        """'This week' = 7-day window ending at reference_time (2024-03-23 to 2024-03-30)."""
        _, data = query_engine.execute({"operation": "count", "time_period": "week"})
        df = data_service.get_data()
        ref = data_service.reference_time
        expected = len(df[df["created_at"] >= ref - pd.Timedelta(days=7)])
        assert data[0]["count"] == expected
        assert data[0]["count"] > 0, "Week filter returned 0 - likely using system clock"

    def test_today_does_not_crash_even_if_empty(self):
        """'Today' relative to reference is a thin slice - must not crash."""
        _, data = query_engine.execute({"operation": "list", "time_period": "today"})
        assert isinstance(data, list)
