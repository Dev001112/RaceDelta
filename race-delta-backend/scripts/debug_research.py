
import sys
print("Python is working")
sys.stdout.flush()
import fastf1
print("FastF1 imported")
sys.stdout.flush()
try:
    s = fastf1.get_event_schedule(2026)
    print(f"Schedule: {len(s)}")
except Exception as e:
    print(e)
