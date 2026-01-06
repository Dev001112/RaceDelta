
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import logging

# Add app to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)

# Import the resolver
from app.utils.season_resolver import resolve_seasons, _build_seasons_dropdown

class TestSeasonTransition(unittest.TestCase):
    
    @patch('app.utils.season_resolver.fastf1.get_event_schedule')
    @patch('app.utils.season_resolver.datetime')
    def test_pre_season_behavior(self, mock_datetime, mock_get_schedule):
        """
        Scenario: It is Jan 1st 2026. Season starts in March.
        Expected: 
            - active_season = None
            - display_season = 2025
            - is_offseason = True
            - Dropdown has "2025 (Last Season)"
        """
        print("\n--- Test 1: Pre-Season (Jan 1 2026) ---")
        
        # Mock "Now" as Jan 1st 2026
        mock_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.utcnow.return_value = mock_now
        
        # Mock Schedule (First race in March)
        # Create a mock DataFrame for schedule
        import pandas as pd
        mock_schedule = pd.DataFrame({
            'Session1Date': [datetime(2026, 3, 1, tzinfo=timezone.utc)],
            'EventDate': [datetime(2026, 3, 5, tzinfo=timezone.utc)]
        })
        mock_get_schedule.return_value = mock_schedule
        
        # Run resolver
        result = resolve_seasons()
        
        # Assertions
        print(f"Result: {result['display_season']} (Is Offseason: {result['is_offseason']})")
        self.assertEqual(result['calendar_season'], 2026)
        self.assertTrue(result['is_offseason'])
        self.assertEqual(result['display_season'], 2025)
        self.assertIsNone(result['active_season'])
        
        # Check dropdown label
        labels = [o['label'] for o in result['seasons_dropdown']]
        print(f"Dropdown: {labels}")
        self.assertIn("2025 (Last Season)", labels)

    @patch('app.utils.season_resolver.fastf1.get_event_schedule')
    @patch('app.utils.season_resolver.datetime')
    def test_in_season_behavior(self, mock_datetime, mock_get_schedule):
        """
        Scenario: It is June 2026. Season started in March.
        Expected: 
            - active_season = 2026
            - display_season = 2026
            - is_offseason = False
            - Dropdown has "2026 (Current)"
        """
        print("\n--- Test 2: In-Season (June 1 2026) ---")
        
        # Mock "Now" as June 1st 2026
        mock_now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.utcnow.return_value = mock_now
        
        # Mock Schedule (First race was March)
        import pandas as pd
        mock_schedule = pd.DataFrame({
            'Session1Date': [datetime(2026, 3, 1, tzinfo=timezone.utc)],
            'EventDate': [datetime(2026, 3, 5, tzinfo=timezone.utc)]
        })
        mock_get_schedule.return_value = mock_schedule
        
        # Run resolver
        result = resolve_seasons()
        
        # Assertions
        print(f"Result: {result['display_season']} (Is Offseason: {result['is_offseason']})")
        self.assertEqual(result['calendar_season'], 2026)
        self.assertFalse(result['is_offseason'])
        self.assertEqual(result['display_season'], 2026)
        self.assertEqual(result['active_season'], 2026)
        
        # Check dropdown label
        labels = [o['label'] for o in result['seasons_dropdown']]
        print(f"Dropdown: {labels}")
        self.assertIn("2026 (Current)", labels)

if __name__ == '__main__':
    unittest.main()
