# Environment Variables Setup

Copy the variables below to a `.env` file in the `race-delta-frontend` directory.

```env
# Backend API Base URL
# Default: http://127.0.0.1:8000
# For production, set to your backend URL
VITE_API_BASE=http://127.0.0.1:8000
```

## Required Variables

- `VITE_API_BASE`: Backend API base URL (defaults to `http://127.0.0.1:8000` if not set)

## Note

Vite requires the `VITE_` prefix for environment variables to be exposed to the frontend code.

