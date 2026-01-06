# Troubleshooting 404 Errors

## Issue: All `/api/*` routes returning 404

### Possible Causes

1. **Import Error Preventing Routes from Loading**
   - If there's an error importing `season_resolver` or any other module, the blueprint won't register
   - Check backend logs for import errors when starting the app

2. **App Not Using create_app()**
   - Ensure `app.py` is using `create_app()` from `app/__init__.py`
   - The app factory pattern must be used for routes to register

3. **Blueprint Not Registered**
   - Routes are in `app/routes.py` with `@api_bp.route()` decorators
   - Blueprint is registered in `app/__init__.py` with `url_prefix="/api"`

### Verification Steps

1. **Check Backend Startup Logs**
   ```bash
   cd race-delta-backend
   python app.py
   ```
   Look for:
   - "ROUTES:" output showing all registered routes
   - Any import errors
   - Any exceptions during startup

2. **Run Test Script**
   ```bash
   python test_routes.py
   ```
   This will show all registered routes and test the health endpoint.

3. **Test Health Endpoint Directly**
   ```bash
   curl http://127.0.0.1:8000/api/health
   ```
   Should return: `{"status": "ok", "service": "RaceDelta API", "version": "1.0.0"}`

4. **Check Browser Network Tab**
   - Open browser DevTools → Network tab
   - Make a request to `/api/drivers`
   - Check the actual URL being requested
   - Check response headers

### Common Fixes

1. **Restart Backend Server**
   - Stop the Flask server (Ctrl+C)
   - Restart: `python app.py`
   - Check for any new error messages

2. **Check for Import Errors**
   - Look for errors related to:
     - `season_resolver`
     - `fastf1`
     - `pandas`
   - All dependencies must be installed: `pip install -r requirements.txt`

3. **Verify Environment Variables**
   - Check `.env` file exists in `race-delta-backend/`
   - Ensure `DATABASE_URL` is set (required for app to start)

4. **Check Python Path**
   - Ensure you're running from `race-delta-backend/` directory
   - Or use: `python -m app` from project root

### Expected Routes

When working correctly, you should see these routes registered:
- `/api/` (health check)
- `/api/health` (health check)
- `/api/seasons`
- `/api/drivers`
- `/api/teams`
- `/api/standings/drivers`
- `/api/standings/constructors`
- `/api/l1/season`
- `/api/compare/drivers`
- `/api/compare/drivers/timeline`

### Debug Output

The improved 404 handler now shows available routes in DEBUG mode. If you see a 404, check the `available_routes` field in the response to see what routes are actually registered.

