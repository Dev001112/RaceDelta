# D:\RaceDelta\race-delta-backend\app.py
from app import create_app
import json, sys

app = create_app()

def print_startup_info(a):
    try:
        print("=== RaceDelta RUNNING INFO ===")
        print("app.import_name:", a.import_name)
        print("app.root_path:", a.root_path)
        print("CWD:", __import__('os').getcwd())
        rules = []
        for r in sorted(a.url_map.iter_rules(), key=lambda x: x.rule):
            rules.append({"rule": r.rule, "endpoint": r.endpoint, "methods": sorted(list(r.methods))})
        print("ROUTES:", json.dumps(rules, indent=2))
        print("=== END RUN INFO ===")
    except Exception as e:
        print("Error printing startup info:", e, file=sys.stderr)

if __name__ == "__main__":
    print_startup_info(app)
    # ensure Flask binds to 0.0.0.0:8000 as requested
    app.run(host="0.0.0.0", port=8000, debug=True)
