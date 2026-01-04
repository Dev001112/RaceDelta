# Environment Variables Setup

Copy the variables below to a `.env` file in the `race-delta-backend` directory.

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=dev-key-change-in-production
DEBUG=True

# Database Configuration
# For SQLite (development):
DATABASE_URL=sqlite:///racedelta.db
# For PostgreSQL (production):
# DATABASE_URL=postgresql://user:password@localhost:5432/racedelta

# OpenF1 API Configuration
OPENF1_BASE=https://api.openf1.org/v1
OPENF1_TIMEOUT=10
OPENF1_CACHE_TTL=300

# Performance Settings
STANDINGS_MAX_RACES=10
ENABLE_STANDINGS_CACHE=true
REQUEST_TIMEOUT=30
```

## Required Variables

- `DATABASE_URL`: Database connection string (required)
- `SECRET_KEY`: Flask secret key for sessions (required in production)

## Optional Variables

All other variables have defaults defined in `config.py` and can be omitted for development.

