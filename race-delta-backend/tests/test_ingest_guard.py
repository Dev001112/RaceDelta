"""The ingestor must refuse a race whose official classification FastF1 has not published yet."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.ingestor import classification_published  # noqa: E402


def test_unpublished_classification_is_detected():
    # timing order (Position) is there within minutes; the official ClassifiedPosition is what matters
    pending = pd.DataFrame({"Abbreviation": ["GAS", "RUS"], "Position": [7.0, 2.0], "ClassifiedPosition": ["", ""], "Status": ["", ""]})
    final = pd.DataFrame({"Abbreviation": ["ANT", "GAS"], "Position": [1.0, 7.0], "ClassifiedPosition": ["1", "7"], "Status": ["Finished", "Finished"]})
    partial = pd.DataFrame({"Abbreviation": ["ANT", "STR"], "Position": [1.0, 20.0], "ClassifiedPosition": ["1", "R"], "Status": ["Finished", "Retired"]})
    assert classification_published(pending) is False
    assert classification_published(final) is True
    assert classification_published(partial) is True          # retirements have no position; that is normal
    assert classification_published(None) is False
    assert classification_published(pd.DataFrame()) is False
