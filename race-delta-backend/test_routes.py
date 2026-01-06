#!/usr/bin/env python3
"""
Quick test script to verify routes are registered correctly.
Run this to check if routes are being loaded.
"""
from app import create_app

app = create_app()

print("=" * 60)
print("REGISTERED ROUTES:")
print("=" * 60)

routes = []
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        routes.append({
            "rule": rule.rule,
            "endpoint": rule.endpoint,
            "methods": sorted(list(rule.methods - {'HEAD', 'OPTIONS'}))
        })

routes.sort(key=lambda x: x["rule"])

for route in routes:
    methods = ", ".join(route["methods"])
    print(f"{route['rule']:40} [{methods:20}] -> {route['endpoint']}")

print("=" * 60)
print(f"Total routes: {len(routes)}")
print("=" * 60)

# Test a specific route
print("\nTesting /api/health endpoint...")
with app.test_client() as client:
    response = client.get('/api/health')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.get_json()}")

print("\nTesting /api/drivers endpoint...")
with app.test_client() as client:
    response = client.get('/api/drivers')
    print(f"Status: {response.status_code}")
    if response.status_code == 404:
        print("ERROR: /api/drivers route not found!")
    else:
        data = response.get_json()
        print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")

