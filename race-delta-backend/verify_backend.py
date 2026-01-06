
import sys
import os
import logging
from datetime import datetime

# Add app to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)

try:
    from app.utils.season_resolver import resolve_seasons
    
    print("Testing resolve_seasons()...")
    result = resolve_seasons()
    print("\n--- Result ---")
    for key, value in result.items():
        print(f"{key}: {value}")
    print("----------------")
    
    # Validation
    assert "calendar_season" in result
    assert "display_season" in result
    assert "is_offseason" in result
    assert isinstance(result["seasons_dropdown"], list)
    
    print("\n✅ season_resolver.py logic verified successfully.")

except Exception as e:
    print(f"\n❌ Error during verification: {e}")
    import traceback
    traceback.print_exc()

