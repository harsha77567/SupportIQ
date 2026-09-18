# SupportIQ — Architecture Walkthrough

## 1. Problem
Support teams have vast amounts of data but lack easy analytical access. SupportIQ provides natural language querying over ticket data without hallucinating metrics, while automatically surfacing critical anomalies.

## 2. Architecture
User -> UI -> FastAPI -> LLM (Intent Parsing) -> Pydantic Validation -> Pandas Engine -> Answer.
This pipeline separates language understanding from mathematical computation.

## 3. Why FastAPI
High performance, native async support, and built-in Pydantic integration for automatic request/response validation and Swagger documentation.

## 4. Why Pandas
For a 500-row dataset, Pandas is the most efficient choice for statistical operations (like IQR for anomalies) without the overhead of spinning up a database container. The architecture isolates data access in `DataService` so it can be swapped to SQL later.

## 5. Why Ollama
It provides local, cost-free LLM inference, ensuring the evaluator can run the project offline at zero cost, fulfilling the core assessment requirements.

## 6. Why LLM-to-intent instead of LLM-generated SQL/code
**Security and Accuracy.** Allowing an LLM to write SQL or Python introduces code injection risks. More importantly, LLMs hallucinate numbers. By having the LLM output a structured JSON intent (e.g. `operation: count`), the deterministic Python engine calculates the exact, verifiable answer.

## 7. Prompt design
The prompt strictly defines the allowed operations, time periods, and fields. It maps specific vocabulary ("unresolved", "open") to exact database statuses to constrain the LLM's imagination.

## 8. Pydantic validation
The `QueryIntent` schema ensures that even if the LLM hallucinates an operation, the application rejects or corrects it before executing.

## 9. Query execution
The `QueryEngine` takes the validated intent, applies Pandas boolean masks for filters, performs groupbys, and formats the final string answer and JSON list.

## 10. Anomaly detection
Uses IQR (Interquartile Range) on resolved tickets for mathematical outlier detection. Uses age calculations for open tickets. It runs automatically, ensuring no critical ticket is missed.

## 11. Historical dataset reference time
Because the dataset is static (e.g., from early 2024), using the computer's current clock would break relative queries like "tickets unresolved for > 24 hours". The system calculates a `reference_time` as the `max(created_at)` in the dataset.

## 12. Error handling
Malformed data causes the app to fail fast on startup with clear error messages. Invalid queries return 400 Bad Request instead of throwing 500 server errors. LLM timeouts gracefully degrade to a regex/heuristic parser.

## 13. Security
No hardcoded secrets. No API keys needed. No execution of arbitrary strings.

## 14. Scalability
The `DataService` could easily be replaced with SQLAlchemy pointing to PostgreSQL. The `query_engine` logic could translate the Intent JSON into a SQLAlchemy ORM query.

## 15. Limitations
The query engine handles the specifically requested assessment queries beautifully but lacks support for complex nested logical OR operations.

## 16. What I would improve with another week
- Add PostgreSQL and SQLAlchemy.
- Implement an evaluation framework to test the LLM prompt against 500 variations of user questions.
- Add vector search on the `issue_summary` field to find duplicate bugs automatically.

## 17. Expected demo flow
1. Start the app. Show Swagger docs.
2. Open UI. Show the dashboard numbers.
3. Show the anomalies section and explain IQR.
4. Run "How many critical tickets are unresolved?" -> Show intent and table.
5. Turn off Ollama (optional) -> Show fallback parser still handling basic questions gracefully.
