import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    dataset_path: str = os.getenv("DATASET_PATH", "data/support_tickets.csv")

settings = Settings()
