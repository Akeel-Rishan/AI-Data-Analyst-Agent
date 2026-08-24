# AI Data Analyst Agent

AI Data Analyst Agent is a containerized foundation for an application that will help users upload, explore, visualize, and analyze datasets with AI assistance. This initial project contains infrastructure and application entry points only; analysis workflows and other business logic will be added later.

## Tech Stack

- FastAPI and Uvicorn for the backend API
- Streamlit for the frontend interface
- PostgreSQL 16 for persistent storage
- SQLAlchemy asyncio and asyncpg for database access
- Pydantic Settings for environment-based configuration
- LangChain, LangGraph, and OpenAI for future agent capabilities
- pandas, NumPy, scikit-learn, Matplotlib, Seaborn, and Plotly for future data analysis
- Docker Compose for local orchestration

## Quick Start

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

   On PowerShell, use `Copy-Item .env.example .env`.

2. Replace `your-openai-api-key-here` in `.env` with your OpenAI API key. For non-development use, also replace the example passwords and secret key.

3. Build and start the application:

   ```bash
   docker compose up --build
   ```

4. Open the services:

   - Frontend: <http://localhost:8501>
   - Backend health check: <http://localhost:8000/health>
   - API documentation: <http://localhost:8000/docs>

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── routers/
│   │   │   └── __init__.py
│   │   ├── agents/
│   │   │   └── __init__.py
│   │   ├── tools/
│   │   │   └── __init__.py
│   │   ├── services/
│   │   │   └── __init__.py
│   │   └── utils/
│   │       └── __init__.py
│   ├── tests/
│   │   └── __init__.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py
│   ├── pages/
│   │   └── __init__.py
│   ├── components/
│   │   └── __init__.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```
