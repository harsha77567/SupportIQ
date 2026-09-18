from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, query, anomalies, summary, tickets
from app.services.data_service import data_service

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SupportIQ API",
    description="AI-Powered Support Ticket Intelligence System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(summary.router, prefix="/api", tags=["Summary"])
app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(anomalies.router, prefix="/api", tags=["Anomalies"])
app.include_router(tickets.router, prefix="/api", tags=["Tickets"])

app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.on_event("startup")
def startup_event():
    try:
        rows = data_service.load_data()
        logger.info(f"Successfully loaded {rows} rows from dataset.")
    except Exception as e:
        logger.error(f"Failed to load dataset on startup: {str(e)}")
