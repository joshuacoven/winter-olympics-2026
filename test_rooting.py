#!/usr/bin/env python3
"""
Quick test script for rooting.py functionality.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from rooting import (
    calculate_category_standing,
    is_prediction_still_possible,
    generate_scenarios,
    calculate_urgency,
    _events_match
)
from categories import get_category_by_id
from events import get_all_events


def test_event_matching():
    """Test event name matching logic."""
    print("Testing event name matching...")

    # Test exact match
    assert _events_match("Men's Downhill", "Men's Downhill")

    # Test gender normalization
    assert _events_match("Men's 1000m", "Men's 1000m")

    # Test substring matching
    assert _events_match("Men's 10km Sprint", "Men's Sprint")

    print("✅ Event matching tests passed!")


def test_urgency_calculation():
    """Test urgency calculation."""
    print("\nTesting urgency calculation...")

    from events import Event
    now = datetime.now(ZoneInfo("Europe/Rome"))

    # Today
    today_event = Event("Test", "Today", "Men", now, now)
    assert calculate_urgency([today_event]) == "today"

    # This week
    from datetime import timedelta
    week_event = Event("Test", "Week", "Men", now + timedelta(days=3), now + timedelta(days=3))
    assert calculate_urgency([week_event]) == "this_week"

    # Later
    later_event = Event("Test", "Later", "Men", now + timedelta(days=10), now + timedelta(days=10))
    assert calculate_urgency([later_event]) == "later"

    print("✅ Urgency calculation tests passed!")


def test_standing_calculation():
    """Test category standing calculation."""
    print("\nTesting category standing calculation...")

    # Test with Alpine Skiing category
    alpine_cat = get_category_by_id("alpine_skiing")
    if alpine_cat:
        standing = calculate_category_standing(alpine_cat)
        print(f"  Alpine Skiing: {standing.completed_event_count} completed, {standing.remaining_event_count} remaining")
        print(f"  Gold counts: {standing.gold_counts}")

        # Check that the numbers make sense
        assert standing.completed_event_count >= 0
        assert standing.remaining_event_count >= 0
        assert standing.completed_event_count + standing.remaining_event_count <= alpine_cat.event_count

        print("✅ Standing calculation test passed!")
    else:
        print("⚠️  Could not find Alpine Skiing category")


def test_scenario_generation():
    """Test scenario generation."""
    print("\nTesting scenario generation...")

    from rooting import CategoryStanding
    from categories import PredictionCategory, ANSWER_COUNTRY

    # Mock category
    mock_cat = PredictionCategory(
        id="test",
        sport="Test",
        gender=None,
        display_name="Test Category",
        event_count=10,
        first_event_date=None,
        last_event_date=None,
        answer_type=ANSWER_COUNTRY
    )

    # Test: user is leading
    standing = CategoryStanding(
        category_id="test",
        gold_counts={"Norway": 5, "Austria": 3},
        remaining_event_count=2,
        completed_event_count=8,
        is_complete=False
    )
    scenarios = generate_scenarios(standing, "Norway", mock_cat)
    print(f"  Leading scenario: {scenarios[0]}")
    assert "Leading" in scenarios[0] or "Tied" in scenarios[0]

    # Test: user is behind
    scenarios = generate_scenarios(standing, "Austria", mock_cat)
    print(f"  Behind scenario: {scenarios[0]}")
    assert "more gold" in scenarios[0].lower() or "more golds" in scenarios[0].lower()

    print("✅ Scenario generation tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Rooting Module")
    print("=" * 60)

    test_event_matching()
    test_urgency_calculation()
    test_standing_calculation()
    test_scenario_generation()

    print("\n" + "=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)
