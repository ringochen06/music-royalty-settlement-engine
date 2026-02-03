# Music Royalty Settlement Engine

A high-throughput financial ledger for music royalty settlements with strict ACID compliance.

## Features

- **Double-Entry Accounting**: Balanced journal entries with zero-sum validation
- **Multi-Party Revenue Splits**: Artist/Label/Producer allocation with BPS precision
- **Micros Precision**: 1e-6 USD precision for fractional cents ($0.0034/stream)
- **Idempotent ETL**: SHA-256 deduplication with business-level idempotency keys
- **ACID Compliance**: PostgreSQL transactions for data consistency

## Tech Stack

- **Backend**: Python 3.12 + FastAPI
- **Database**: PostgreSQL 16
- **Deployment**: Docker Compose

## Quick Start

```bash
# Start services
docker compose up -d

# Access API docs
open http://localhost:8000/docs
```

## Key Concepts

### Micros (1e-6 USD)
All monetary amounts are stored in micros to handle fractional cents:
- $1.00 = 1,000,000 micros
- $0.0034 = 3,400 micros

### Basis Points (BPS)
Ratios are expressed in basis points:
- 1 BPS = 0.01%
- 10000 BPS = 100%
- 5000 BPS = 50%

### Business Idempotency
Operations use `statement_id` as the primary idempotency key, with SHA-256 hashes as secondary protection.

## Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
```

## License

MIT
