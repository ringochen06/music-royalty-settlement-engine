"""Music Royalty Settlement Engine API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.ledger.router import router as ledger_router

app = FastAPI(
    title="Music Royalty Settlement Engine",
    description="""
Financial ledger for music royalty settlements.

- Double-entry accounting
- Multi-party revenue splits
- Micros precision (1e-6 USD)
- Idempotent ETL
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {"status": "healthy", "environment": settings.environment}


@app.get("/", tags=["Root"])
def root() -> dict:
    return {"name": "Music Royalty Settlement Engine", "version": "1.0.0", "docs": "/docs"}


app.include_router(ledger_router, prefix=f"{settings.api_v1_prefix}/ledger", tags=["Ledger"])

# TODO: Add remaining routers
# app.include_router(parties_router, prefix=f"{settings.api_v1_prefix}/parties")
# app.include_router(contracts_router, prefix=f"{settings.api_v1_prefix}/contracts")
# app.include_router(ingestion_router, prefix=f"{settings.api_v1_prefix}/ingestion")
# app.include_router(settlement_router, prefix=f"{settings.api_v1_prefix}/settlements")
# app.include_router(reports_router, prefix=f"{settings.api_v1_prefix}/reports")
