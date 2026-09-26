# StockSense Backend

StockSense is a modular Inventory Management System backend built with Python, FastAPI, SQLAlchemy 2.x, and Pydantic.

## Prerequisites

- Python 3.11+
- virtualenv / venv (recommended)

## Project Architecture

```text
backend/
  app/
    __init__.py
    main.py             # FastAPI application initialization and CORS setup
    config.py           # Environment settings (Pydantic Settings)
    database.py         # SQLAlchemy engine, SessionLocal, Base, and get_db dependency
    models/             # SQLAlchemy 2.x ORM models & database enums
      __init__.py
      enums.py
      models.py
    schemas/            # Pydantic schemas for API request/response validation
      __init__.py
      health.py
    routers/            # API routers / endpoints
      __init__.py
      health.py
    services/           # Business logic & centralized services
      __init__.py
      inventory_service.py # Centralized Inventory Service placeholder
    middleware/         # Custom FastAPI middleware
    utils/              # Helper functions & utilities
  tests/                # Test suite with pytest
    conftest.py
    test_health.py
    test_models.py
  requirements.txt      # Python dependencies
  .env.example          # Sample environment configuration
  README.md             # Project setup and usage instructions
  docs/
    api.md              # API documentation
```

## Quick Start (Local Setup)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables (optional for local SQLite):
   ```bash
   cp .env.example .env
   ```
   *Note: If `DATABASE_URL` is omitted or left as `sqlite:///./stocksense.db`, local SQLite will be used automatically.*

5. Run the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. Open your browser:
   - Interactive Swagger API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc API Docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

## Running Tests

Run the test suite using `pytest`:

```bash
pytest
```
