# SupportIQ — AI Support Ticket Intelligence

## 1. Project overview
SupportIQ is an AI-powered system designed to analyze customer support ticket datasets. It allows users to query ticket data using natural language, view real-time statistics on a polished dashboard, and automatically detect anomalies (such as severely aging tickets or abnormally long resolution times).

## 2. Problem statement
Customer support teams generate large amounts of data, but extracting actionable insights often requires technical SQL skills or manual spreadsheet manipulation. SupportIQ solves this by providing a natural language interface over support data, lowering the barrier to data intelligence while strictly preventing AI hallucinations on numerical metrics.

## 3. Features
- **Data Ingestion:** Automatically parses, validates, and cleans the support ticket CSV.
- **Natural Language Querying:** Translates user questions into structured JSON intents via a local LLM, then executes deterministic Pandas queries.
- **Anomaly Detection:** Flags statistically long resolution times (IQR method), aging high-priority tickets, and all unresolved critical tickets.
- **REST API:** Robust FastAPI backend with automatic Swagger documentation.
- **Modern UI:** A clean, responsive dashboard presenting summary metrics, anomaly cards, and query results.

## 4. Architecture
The system uses a pipeline architecture to ensure absolute accuracy on analytical results:

```mermaid
flowchart TD
    User([User]) --> UI[Web Dashboard]
    UI --> API[FastAPI Endpoints]
    API --> LLM[Ollama LLM (llama3.2:3b)]
    LLM -- JSON Intent --> Validator[Pydantic Validation]
    Validator --> Engine[Pandas Analytics Engine]
    Engine --> CSV[(support_tickets.csv)]
    Engine -- Query Result --> API
    API --> UI
```

## 5. Why this architecture?
The core principle of SupportIQ is: **LLM = Natural language understanding, Python = Actual computation**.
By forcing the LLM to output a strictly structured intent (e.g., `{"operation": "count", "filters": {"status": "Open"}}`) and validating it with Pydantic, the system completely avoids hallucinations on numerical answers. The deterministic Pandas engine runs the actual math.

## 6. Technology stack
- **Python** (Backend Logic)
- **FastAPI** (REST API)
- **Pandas** (Data Processing & Analytics)
- **Pydantic** (Validation & Schema Definition)
- **Ollama** (Local LLM Integration)
- **HTML/CSS/JavaScript** (Frontend UI)
- **Pytest** (Automated Testing)

## 7. Dataset schema
The application consumes a 500-row `support_tickets.csv` with the following schema:
- `ticket_id`: string, Unique identifier
- `created_at`: datetime, Creation timestamp
- `category`: "Billing", "Technical", "General"
- `priority`: "Low", "Medium", "High", "Critical"
- `status`: "Open", "Resolved", "Escalated"
- `response_time_hrs`: float, Hours to first response
- `resolution_time_hrs`: float, Hours to resolution (null if unresolved)
- `agent_id`: string, Assigned agent
- `customer_rating`: int 1-5, User rating
- `issue_summary`: string, Free-text description

## 8. Setup
**Prerequisites:** Python 3.10+ and Ollama.

1. **Clone & Environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Setup LLM:**
   Ensure Ollama is installed and running, then pull the model:
   ```bash
   ollama pull llama3.2:3b
   ```
4. **Run Application:**
   ```bash
   uvicorn app.main:app --reload
   ```
5. **Access:**
   - Web UI: http://127.0.0.1:8000
   - Swagger API Docs: http://127.0.0.1:8000/docs

## 9. API documentation
- `GET /api/health`: Health check and dataset row count validation.
- `GET /api/summary`: Returns top-level summary metrics (Total, Open, Escalated, Resolved, Avg Rating).
- `POST /api/query`: Accepts natural language and returns answers alongside the parsed intent and structured data.
- `GET /api/anomalies?threshold_hours=24`: Returns classified anomalies for the dataset.
- `GET /api/tickets`: Returns the raw data list.

## 10. Example queries (Verified on Dataset)
All values are pre-verified against the real 500-row CSV.
Dataset `reference_time = 2024-03-30 18:06:00` (max `created_at`).

| Query | Answer |
|---|---|
| How many tickets are currently open? | **111** |
| How many critical tickets are unresolved? | **31** (Open + Escalated) |
| Which agent resolved the most tickets this month? | **AGT-01** (16 tickets, March 2024) |
| Which agent resolved the most tickets all-time? | **AGT-09** (37 tickets) |
| Which agent has the lowest average customer rating? | **AGT-08** (avg 3.48) |
| Average customer rating for Technical tickets? | **3.74** |
| How many escalated tickets are there? | **62** |
| Tickets with resolution time above 20 hours? | **106** |
| Tickets in the reference week (last 7 days from ref)? | **55** |
| Resolved tickets this month? | **121** |
| Billing average resolution time? | **16.33 hrs** |

### Anomaly Detection (threshold=24h)
| Category | Count |
|---|---|
| Statistical outliers (IQR upper bound: 48.15 hrs) | **21** |
| Aging High/Critical unresolved (>24h) | **80** |
| Unresolved Critical tickets | **31** |
| **Total anomalies** | **132** |

### 12-hour null-handling edge case
The query *Show me all Critical tickets not resolved within 12 hours* returns **34 tickets**.
A naive `resolution_time_hrs > 12` filter returns only **3** because it silently drops rows
where `resolution_time_hrs` is NULL (all unresolved tickets). The correct filter applies:
- Resolved tickets where `resolution_time_hrs > 12`
- Unresolved tickets where `age_from_reference_time > 12`

## 11. LLM design
The LLM is prompted with the exact dataset fields and allowed operations. It converts questions like "How many critical tickets are unresolved?" into `{"operation": "count", "filters": {"priority": "Critical", "status": "unresolved"}}`. If Ollama is down, a deterministic fallback heuristic kicks in to ensure the application remains functional.

## 12. Anomaly detection methodology
- **Statistical Outliers:** Uses the Interquartile Range (IQR) on `resolution_time_hrs`. Any resolved ticket exceeding Q3 + 1.5 * IQR is flagged.
- **Aging High/Critical:** Calculates age using `reference_time - created_at`. Flags open/escalated high/critical tickets older than the threshold (default 24h).
- **Historical Reference:** `reference_time` is dynamically set to the maximum `created_at` in the dataset to simulate a point-in-time analysis, ensuring relative terms like "today" or "aging" work regardless of when the app is run.

## 13. Error handling
- **Startup:** App validates required columns, uniqueness, and enum boundaries on boot. Fails fast with clear exceptions if data is corrupt.
- **LLM/Query:** Invalid JSON from the LLM is caught, falling back to the heuristic parser.
- **API Responses:** Errors are returned as standard HTTP 400 responses with descriptive `detail` payloads.

## 14. Security
No arbitrary code execution (no `eval`, `exec`, or LLM-generated SQL). All LLM output is parsed as static JSON and validated against strict Pydantic schemas.

## 15. Known limitations
- The deterministic query engine (`app/analytics/query_engine.py`) supports a specific subset of operations. Complex nested filtering (e.g., OR conditions) currently requires expanding the intent schema.
- Pandas runs in-memory. Suitable for 500 rows, but memory limits will be hit at massive scale.

## 16. Scalability / future improvements
- **Database:** Migrate from Pandas to PostgreSQL for handling millions of rows.
- **Vector Search:** Add embeddings on the `issue_summary` column to allow semantic searches (e.g., "Find tickets about login bugs").
- **Async Processing:** Move anomaly detection to a background Celery task.
- **Observability:** Add Prometheus metrics to track intent parsing accuracy over time.

## 17. Architecture trade-offs
Using pandas instead of a SQL database trades scalability for simplicity in this assessment. Using an LLM to generate Intents instead of SQL trades query flexibility for security and absolute determinism on metrics.
