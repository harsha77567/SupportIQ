import pandas as pd
from typing import Dict, Any, List
from app.services.data_service import data_service

class QueryEngine:
    def __init__(self):
        pass

    def execute(self, intent: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        df = data_service.get_data().copy()
        reference_time = data_service.reference_time
        
        filters = intent.get("filters", {})
        
        # Apply Filters
        if filters:
            if "status" in filters:
                if filters["status"].lower() == "unresolved":
                    df = df[df["status"].isin(["Open", "Escalated"])]
                else:
                    df = df[df["status"].str.lower() == filters["status"].lower()]
                    
            if "priority" in filters:
                df = df[df["priority"].str.lower() == filters["priority"].lower()]
                
            if "category" in filters:
                df = df[df["category"].str.lower() == filters["category"].lower()]
                
            if "age_greater_than" in filters:
                age_hrs = (reference_time - df["created_at"]).dt.total_seconds() / 3600
                df = df[age_hrs > float(filters["age_greater_than"])]
                
            if "resolution_time_greater_than" in filters:
                df = df[df["resolution_time_hrs"] > float(filters["resolution_time_greater_than"])]
                
            if "not_resolved_within_hrs" in filters:
                hrs = float(filters["not_resolved_within_hrs"])
                age_hrs = (reference_time - df["created_at"]).dt.total_seconds() / 3600
                # Condition 1: It is resolved, but it took longer than X hours
                cond1 = df["resolution_time_hrs"] > hrs
                # Condition 2: It is unresolved (resolution time is NA), and its age is > X hours
                cond2 = df["resolution_time_hrs"].isna() & (age_hrs > hrs)
                df = df[cond1 | cond2]

        # Time Period
        time_period = intent.get("time_period")
        if time_period == "month":
            df = df[(df["created_at"].dt.year == reference_time.year) & 
                    (df["created_at"].dt.month == reference_time.month)]
        elif time_period == "week":
            df = df[df["created_at"] >= (reference_time - pd.Timedelta(days=7))]
        elif time_period == "today":
            df = df[df["created_at"].dt.date == reference_time.date()]

        operation = intent.get("operation", "list")
        metric = intent.get("metric")
        group_by = intent.get("group_by")
        limit = intent.get("limit")
        
        result_data = []
        answer = ""

        if operation == "count":
            count = len(df)
            answer = f"Found {count} tickets."
            result_data = [{"count": count}]
            
        elif operation == "average":
            if not metric or metric not in df.columns:
                answer = "Invalid or missing metric for average."
            else:
                avg = df[metric].mean()
                avg_val = round(avg, 2) if pd.notna(avg) else 0
                answer = f"The average {metric} is {avg_val}."
                result_data = [{metric: avg_val}]
                
        elif operation == "list":
            if limit:
                df = df.head(limit)
            # dropna is important for json serialization of NaN
            result_data = df.fillna("").to_dict(orient="records")
            answer = f"Found {len(result_data)} tickets."
            
        elif operation in ["top", "bottom"]:
            if not group_by:
                answer = "Grouping field missing."
            else:
                if metric == "ticket_count" or not metric:
                    grouped = df.groupby(group_by).size().reset_index(name="count")
                    sort_col = "count"
                else:
                    grouped = df.groupby(group_by)[metric].mean().reset_index()
                    sort_col = metric
                    
                ascending = True if operation == "bottom" else False
                grouped = grouped.sort_values(by=sort_col, ascending=ascending)
                
                if limit:
                    grouped = grouped.head(limit)
                    
                result_data = grouped.fillna("").to_dict(orient="records")
                if result_data:
                    top_val = result_data[0][group_by]
                    val = result_data[0][sort_col]
                    val_str = round(val, 2) if isinstance(val, float) else val
                    answer = f"The {operation} {group_by} is {top_val} with {val_str}."
                else:
                    answer = "No data found."
                    
        elif operation == "group_average":
             if not group_by or not metric:
                 answer = "Grouping or metric missing."
             else:
                 grouped = df.groupby(group_by)[metric].mean().reset_index()
                 result_data = grouped.fillna("").to_dict(orient="records")
                 answer = f"Found average {metric} by {group_by}."
                 
        else:
            answer = f"Unsupported operation: {operation}"
            
        return answer, result_data

query_engine = QueryEngine()
