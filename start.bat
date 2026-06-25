@echo off
echo ============================================
echo   DocMind AI v2.0 — Startup Script
echo ============================================
echo.
echo IMPORTANT: Before running, ensure:
echo   1. PostgreSQL is running
echo   2. Update DATABASE_URL in .env with your DB credentials
echo   3. (Optional) Start Qdrant: docker run -p 6333:6333 qdrant/qdrant
echo      OR update QDRANT_URL in .env for Qdrant Cloud
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    pause
    exit /b 1
)

:: Create the PostgreSQL database if needed
echo Step 1: Creating database (if not exists)...
python -c "
import psycopg2
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL', '').replace('+asyncpg', '')
try:
    result = urlparse(db_url)
    conn = psycopg2.connect(
        host=result.hostname or 'localhost',
        port=result.port or 5432,
        user=result.username or 'postgres',
        password=result.password or '',
        database='postgres'
    )
    conn.autocommit = True
    cur = conn.cursor()
    dbname = result.path.lstrip('/')
    cur.execute(f\"SELECT 1 FROM pg_database WHERE datname = '{dbname}'\")
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE {dbname}')
        print(f'Created database: {dbname}')
    else:
        print(f'Database already exists: {dbname}')
    conn.close()
except Exception as e:
    print(f'DB setup warning (may be OK if using Cloud DB): {e}')
"

echo.
echo Step 2: Starting DocMind AI backend on http://localhost:8000
echo   Open http://localhost:8000 in your browser
echo   API docs available at http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server.
echo.

echo Changing working directory to script location...
pushd "%~dp0"

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

popd
