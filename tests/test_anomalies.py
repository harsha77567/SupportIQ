"""
Unit tests for the AnomalyDetector against the real 500-row dataset.

Pre-verified values:
  reference_time         = 2024-03-30 18:06:00
  IQR upper bound        = 48.15 hrs
  Statistical outliers   = 21
  Aging HP >24h          = 80
  Unresolved Critical    = 31
"""
import pytest
import pandas as pd
from app.services.data_service import data_service
from app.analytics.anomaly_detector import anomaly_detector


@pytest.fixture(autouse=True, scope="module")
def load_data():
    data_service.load_data()


class TestAnomalyDetectorResults:

    def test_reference_time_is_max_created_at(self):
        """reference_time must be the dataset maximum, not system clock."""
        result = anomaly_detector.detect_anomalies()
        expected_ref = data_service.reference_time.isoformat()
        assert result["reference_time"] == expected_ref

    def test_resolution_outliers_count(self):
        """Statistical outliers (IQR method) -> 21 resolved tickets."""
        result = anomaly_detector.detect_anomalies()
        assert len(result["statistical_outliers"]) == 21

    def test_resolution_outliers_all_resolved(self):
        """All statistical outliers must have status=Resolved."""
        result = anomaly_detector.detect_anomalies()
        for a in result["statistical_outliers"]:
            assert a.status == "Resolved", (
                f"Ticket {a.ticket_id} is a resolution-time outlier but status={a.status}"
            )

    def test_resolution_outliers_exceed_iqr_bound(self):
        """Each outlier's resolution_time_hrs must exceed the IQR upper bound."""
        result = anomaly_detector.detect_anomalies()
        bound = result["resolution_time_upper_bound_hrs"]
        assert bound is not None
        assert abs(bound - 48.15) < 0.5   # verified pre-computed value
        for a in result["statistical_outliers"]:
            assert a.resolution_time_hrs > bound, (
                f"Ticket {a.ticket_id} has resolution_time={a.resolution_time_hrs} "
                f"but bound={bound}"
            )

    def test_aging_high_priority_count(self):
        """High/Critical unresolved tickets older than 24h -> 80."""
        result = anomaly_detector.detect_anomalies(threshold_hours=24.0)
        assert len(result["aging_high_priority"]) == 80

    def test_aging_high_priority_all_unresolved(self):
        """All aging tickets must be Open or Escalated."""
        result = anomaly_detector.detect_anomalies()
        for a in result["aging_high_priority"]:
            assert a.status in ("Open", "Escalated")

    def test_aging_high_priority_correct_priority_levels(self):
        """Only High and Critical tickets are flagged as aging HP."""
        result = anomaly_detector.detect_anomalies()
        for a in result["aging_high_priority"]:
            assert a.priority in ("High", "Critical"), (
                f"Ticket {a.ticket_id} has priority={a.priority} "
                "but only High/Critical should be flagged as aging"
            )

    def test_aging_high_priority_age_exceeds_threshold(self):
        """All aging tickets must have age_hours > 24."""
        result = anomaly_detector.detect_anomalies(threshold_hours=24.0)
        for a in result["aging_high_priority"]:
            assert a.age_hours > 24.0, (
                f"Ticket {a.ticket_id} age_hours={a.age_hours} does not exceed threshold 24"
            )

    def test_unresolved_critical_count(self):
        """Unresolved Critical tickets -> 31."""
        result = anomaly_detector.detect_anomalies()
        assert len(result["unresolved_critical"]) == 31

    def test_unresolved_critical_all_critical_priority(self):
        """Every unresolved_critical ticket must be priority=Critical."""
        result = anomaly_detector.detect_anomalies()
        for a in result["unresolved_critical"]:
            assert a.priority == "Critical"

    def test_unresolved_critical_all_unresolved(self):
        """Every unresolved_critical ticket must be Open or Escalated."""
        result = anomaly_detector.detect_anomalies()
        for a in result["unresolved_critical"]:
            assert a.status in ("Open", "Escalated")

    def test_total_anomalies_is_sum_of_three_lists(self):
        """total_anomalies == len(outliers) + len(aging_hp) + len(unresolved_critical)."""
        result = anomaly_detector.detect_anomalies()
        expected = (
            len(result["statistical_outliers"])
            + len(result["aging_high_priority"])
            + len(result["unresolved_critical"])
        )
        assert result["total_anomalies"] == expected

    def test_custom_threshold_reduces_aging_count(self):
        """Higher threshold means fewer aging tickets flagged."""
        low_result = anomaly_detector.detect_anomalies(threshold_hours=24.0)
        high_result = anomaly_detector.detect_anomalies(threshold_hours=200.0)
        assert len(high_result["aging_high_priority"]) <= len(low_result["aging_high_priority"])

    def test_anomaly_tickets_have_required_fields(self):
        """Every anomaly object must carry ticket_id, priority, status, anomaly_reason."""
        result = anomaly_detector.detect_anomalies()
        all_anomalies = (
            result["statistical_outliers"]
            + result["aging_high_priority"]
            + result["unresolved_critical"]
        )
        for a in all_anomalies:
            assert a.ticket_id, "ticket_id must not be empty"
            assert a.priority, "priority must not be empty"
            assert a.status, "status must not be empty"
            assert a.anomaly_reason, "anomaly_reason must not be empty"
