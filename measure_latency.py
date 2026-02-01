import requests
import time
import sys

BASE_URL = "http://localhost:5000"

def measure_endpoint(endpoint):
    url = f"{BASE_URL}{endpoint}"
    print(f"Testing {url}...")
    start = time.time()
    try:
        response = requests.get(url)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            count = data.get("count") or len(data.get("drivers", [])) or len(data.get("races", []))
            source = data.get("source", "unknown")
            print(f"SUCCESS: {duration:.4f}s | Source: {source} | Items: {count}")
            return duration, source
        else:
            print(f"FAILED: {response.status_code} in {duration:.4f}s")
            return duration, "error"
    except Exception as e:
        print(f"ERROR: {e}")
        return 0, "error"

if __name__ == "__main__":
    print("--- Performance Benchmark ---")
    
    # Warm up / Check 2025 Drivers
    print("\n1. Fetching 2025 Drivers (First Attempt)")
    t1, s1 = measure_endpoint("/api/drivers/2025")
    
    if s1 == "empty":
        print("   (Note: DB was empty, this might have triggered ingestion?)")

    # Second Attempt (Should be cached/DB)
    print("\n2. Fetching 2025 Drivers (Second Attempt)")
    t2, s2 = measure_endpoint("/api/drivers/2025")
    
    # Check Schedule
    print("\n3. Fetching 2025 Schedule")
    t3, s3 = measure_endpoint("/api/races/2025")
    
    print("\n--- Summary ---")
    print(f"Drivers (1st call): {t1:.4f}s ({s1})")
    print(f"Drivers (2nd call): {t2:.4f}s ({s2})")
    print(f"Schedule:           {t3:.4f}s ({s3})")
    
    if t2 < 0.1:
        print("\nRESULT: Excellent. Postgres/Cache is working.")
    elif t2 < 1.0:
        print("\nRESULT: Acceptable. Could be faster.")
    else:
        print("\nRESULT: SLOW. Something is wrong with DB or detailed fetching.")
