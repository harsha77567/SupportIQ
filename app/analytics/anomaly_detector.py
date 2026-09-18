import pandas as pd
from typing import Dict, Any
from app.services.data_service import data_service
from app.schemas import TicketAnomaly

class AnomalyDetector:
    def __init__(self):
        pass
        
    def detect_anomalies(self, threshold_hours: float = 24.0) -> Dict[str, Any]:
        df = data_service.get_data().copy()
        reference_time = data_service.reference_time
        
        # 1. Statistical Outliers in Resolution Time
        resolved_df = df[df["status"] == "Resolved"].copy()
        q1 = resolved_df["resolution_time_hrs"].quantile(0.25)
        q3 = resolved_df["resolution_time_hrs"].quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr
        
        outliers = resolved_df[resolved_df["resolution_time_hrs"] > upper_bound]
        
        statistical_outliers = []
        for _, row in outliers.iterrows():
            statistical_outliers.append(TicketAnomaly(
                ticket_id=row["ticket_id"],
                priority=row["priority"],
                category=row["category"],
                agent_id=str(row["agent_id"]) if pd.notna(row["agent_id"]) else None,
                created_at=row["created_at"].isoformat(),
                issue_summary=str(row["issue_summary"]) if pd.notna(row["issue_summary"]) else None,
                anomaly_reason="Abnormally long resolution time",
                resolution_time_hrs=row["resolution_time_hrs"],
                status=row["status"]
            ))
            
        # 2. Unresolved high-priority tickets older than threshold
        unresolved_df = df[df["status"].isin(["Open", "Escalated"])].copy()
        unresolved_df["age_hours"] = (reference_time - unresolved_df["created_at"]).dt.total_seconds() / 3600
        
        aging_hp = unresolved_df[
            (unresolved_df["priority"].isin(["High", "Critical"])) & 
            (unresolved_df["age_hours"] > threshold_hours)
        ]
        
        aging_high_priority = []
        for _, row in aging_hp.iterrows():
            aging_high_priority.append(TicketAnomaly(
                ticket_id=row["ticket_id"],
                priority=row["priority"],
                category=row["category"],
                agent_id=str(row["agent_id"]) if pd.notna(row["agent_id"]) else None,
                created_at=row["created_at"].isoformat(),
                issue_summary=str(row["issue_summary"]) if pd.notna(row["issue_summary"]) else None,
                anomaly_reason=f"Unresolved high priority ticket older than {threshold_hours}h",
                age_hours=row["age_hours"],
                status=row["status"]
            ))
            
        # 3. Unresolved Critical tickets
        critical_unresolved = unresolved_df[unresolved_df["priority"] == "Critical"]
        
        unresolved_critical = []
        for _, row in critical_unresolved.iterrows():
            unresolved_critical.append(TicketAnomaly(
                ticket_id=row["ticket_id"],
                priority=row["priority"],
                category=row["category"],
                agent_id=str(row["agent_id"]) if pd.notna(row["agent_id"]) else None,
                created_at=row["created_at"].isoformat(),
                issue_summary=str(row["issue_summary"]) if pd.notna(row["issue_summary"]) else None,
                anomaly_reason="Unresolved Critical ticket",
                age_hours=row["age_hours"],
                status=row["status"]
            ))
            
        return {
            "reference_time": reference_time.isoformat(),
            "resolution_time_upper_bound_hrs": float(upper_bound) if pd.notna(upper_bound) else None,
            "statistical_outliers": statistical_outliers,
            "aging_high_priority": aging_high_priority,
            "unresolved_critical": unresolved_critical,
            "total_anomalies": len(statistical_outliers) + len(aging_high_priority) + len(unresolved_critical)
        }

anomaly_detector = AnomalyDetector()
