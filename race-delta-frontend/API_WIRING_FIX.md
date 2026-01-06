# Frontend-Backend API Wiring Fix

## Issues Found and Fixed

### 1. Inconsistent API Base URL Handling
**Problem**: The `src/api/client.js` didn't handle cases where `VITE_API_BASE` might include `/api` suffix, which could cause double `/api` in URLs.

**Fix**: Added `normalizeBaseUrl()` function that:
- Removes trailing `/api` from the base URL if present
- Ensures all paths are normalized to include `/api` prefix
- Works correctly whether `VITE_API_BASE` is set to `http://127.0.0.1:8000` or `http://127.0.0.1:8000/api`

### 2. Path Normalization
**Problem**: Paths needed to consistently include `/api` prefix.

**Fix**: Updated `safeFetch()` to:
- Automatically ensure paths start with `/api`
- Handle both `/api/drivers` and `/drivers` formats correctly

## Current API Client Setup

**File**: `src/api/client.js`
- Base URL: Normalized to NOT include `/api` suffix
- All paths: Automatically prefixed with `/api`
- CORS: Enabled in backend (`CORS(app)` in `app/__init__.py`)

## Backend API Endpoints

All endpoints are registered with `/api` prefix:
- `/api/drivers` - Get drivers list
- `/api/teams` - Get teams list
- `/api/standings/drivers` - Get driver standings
- `/api/standings/constructors` - Get constructor standings
- `/api/seasons` - Get season information
- `/api/l1/season` - Get driver season analytics
- `/api/compare/drivers` - Compare two drivers

## Environment Variable

Set in `.env` file (or environment):
```env
VITE_API_BASE=http://127.0.0.1:8000
```

Or with `/api` suffix (both work now):
```env
VITE_API_BASE=http://127.0.0.1:8000/api
```

## Testing

To verify API calls are working:

1. Check browser console for network requests
2. Look for `[client] fetch ->` debug logs
3. Verify CORS headers in network tab
4. Check backend logs for incoming requests

## Troubleshooting

If API calls still fail:

1. **CORS Issues**: Verify backend CORS is enabled (it is in `app/__init__.py`)
2. **Backend Not Running**: Ensure Flask backend is running on port 8000
3. **Wrong Port**: Check `VITE_API_BASE` matches backend port
4. **Network Errors**: Check browser console for specific error messages

