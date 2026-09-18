import pandas as pd
import numpy as np
import os
from app.config import settings

class DataService:
    def __init__(self):
        self.df = None
        self.reference_time = None
        
    def load_data(self):
        if not os.path.exists(settings.dataset_path):
            raise FileNotFoundError(f"Dataset not found at {settings.dataset_path}")
            
        df = pd.read_csv(settings.dataset_path)
        
        # Validate columns
        expected_cols = [
            "ticket_id", "created_at", "category", "priority", "status", 
            "response_time_hrs", "resolution_time_hrs", "agent_id", 
            "customer_rating", "issue_summary"
        ]
        
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing columns in dataset: {missing_cols}")
            
        # Parse dates
        df["created_at"] = pd.to_datetime(df["created_at"], errors='coerce')
        if df["created_at"].isna().any():
            raise ValueError("Invalid date format in created_at column")
            
        # Validate uniqueness
        if df["ticket_id"].duplicated().any():
            raise ValueError("Duplicate ticket_id found")
            
        # Validate categorical values
        valid_categories = {"Billing", "Technical", "General"}
        valid_priorities = {"Low", "Medium", "High", "Critical"}
        valid_statuses = {"Open", "Resolved", "Escalated"}
        
        if not set(df["category"].dropna().unique()).issubset(valid_categories):
            raise ValueError("Invalid category values")
        if not set(df["priority"].dropna().unique()).issubset(valid_priorities):
            raise ValueError("Invalid priority values")
        if not set(df["status"].dropna().unique()).issubset(valid_statuses):
            raise ValueError("Invalid status values")
            
        self.df = df
        self.reference_time = df["created_at"].max()
        return len(df)
        
    def get_data(self):
        if self.df is None:
            self.load_data()
        return self.df

data_service = DataService()
