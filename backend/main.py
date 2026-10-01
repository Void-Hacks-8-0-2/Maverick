"""
Main Application Entrypoint for Operation 'ABHEDYA-CHAKRA'
Base v0.1: Financial Cyber-Forensics & Network Investigation Platform
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.db.connection import get_db, get_dataset_path
from backend.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm DuckDB connection and ensure Parquet view exists
    db_path = get_dataset_path()
    print(f"[STARTUP] Initializing Abhedya-Chakra Base v0.1 backend...")
    print(f"[STARTUP] Production Dataset Source: {db_path}")
    con = get_db()
    row_count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"[STARTUP] Verified DuckDB table loaded successfully ({row_count:,} records).")
    yield
    print("[SHUTDOWN] Closing Abhedya-Chakra backend.")


app = FastAPI(
    title="Operation 'Abhedya-Chakra' API",
    version="0.1.0-base",
    description="Financial Cyber-Forensics & Money-Mule Network Investigation API",
    lifespan=lifespan
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes under /api
app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "Operation 'Abhedya-Chakra' API",
        "version": "0.1.0-base",
        "documentation": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
