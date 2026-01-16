"""
Prediction Categories for Winter Olympics 2026

Instead of predicting individual event winners, users predict which country
wins the most gold medals in each sport+gender category.
"""

from dataclasses import dataclass
from datetime import datetime
from events import get_all_events, WINTER_OLYMPICS_COUNTRIES


@dataclass
class PredictionCategory:
    """Represents a category for prediction (sport + gender combination)."""
    id: str              # e.g., "alpine_skiing_men"
    sport: str           # e.g., "Alpine Skiing"
    gender: str | None   # "Men", "Women", "Mixed", or None for Overall
    display_name: str    # e.g., "Men's Alpine Skiing"
    event_count: int     # Number of gold medals in this category
    first_event_date: datetime | None  # When first event starts
    last_event_date: datetime | None   # When last event ends

    @property
    def is_overall(self) -> bool:
        """Check if this is the Overall category."""
        return self.gender is None and self.sport == "Overall"


def generate_categories() -> list[PredictionCategory]:
    """
    Generate all prediction categories from the events data.
    Groups events by sport+gender and creates one category per combination.
    Also adds an "Overall" category for most total gold medals.
    """
    events = get_all_events()

    # Group events by sport+gender
    category_map: dict[tuple[str, str], list] = {}

    for event in events:
        key = (event.sport, event.gender)
        if key not in category_map:
            category_map[key] = []
        category_map[key].append(event)

    categories = []

    # Create categories from grouped events
    for (sport, gender), event_list in sorted(category_map.items()):
        # Generate ID (lowercase, underscores)
        cat_id = f"{sport.lower().replace(' ', '_').replace('-', '_')}_{gender.lower()}"

        # Generate display name
        if gender == "Mixed":
            display_name = f"Mixed {sport}"
        else:
            display_name = f"{gender}'s {sport}"

        # Get date range
        first_date = min(e.first_round_date for e in event_list)
        last_date = max(e.gold_medal_date for e in event_list)

        categories.append(PredictionCategory(
            id=cat_id,
            sport=sport,
            gender=gender,
            display_name=display_name,
            event_count=len(event_list),
            first_event_date=first_date,
            last_event_date=last_date
        ))

    # Add Overall category
    total_events = len(events)
    first_overall = min(e.first_round_date for e in events)
    last_overall = max(e.gold_medal_date for e in events)

    categories.append(PredictionCategory(
        id="overall",
        sport="Overall",
        gender=None,
        display_name="Most Gold Medals Overall",
        event_count=total_events,
        first_event_date=first_overall,
        last_event_date=last_overall
    ))

    return categories


def get_all_categories() -> list[PredictionCategory]:
    """Return all prediction categories."""
    return generate_categories()


def get_category_by_id(category_id: str) -> PredictionCategory | None:
    """Get a specific category by ID."""
    for cat in get_all_categories():
        if cat.id == category_id:
            return cat
    return None


def get_categories_by_sport(sport: str) -> list[PredictionCategory]:
    """Get all categories for a specific sport."""
    return [c for c in get_all_categories() if c.sport == sport]


def get_sports_list() -> list[str]:
    """Get list of unique sports (excluding Overall)."""
    categories = get_all_categories()
    sports = set(c.sport for c in categories if not c.is_overall)
    return sorted(sports)


def get_countries() -> list[str]:
    """Return list of countries for prediction dropdowns."""
    return WINTER_OLYMPICS_COUNTRIES


if __name__ == "__main__":
    # Print summary for verification
    categories = get_all_categories()

    print(f"Total categories: {len(categories)}")
    print("\nCategories by sport:")

    current_sport = None
    for cat in categories:
        if cat.sport != current_sport:
            current_sport = cat.sport
            print(f"\n{current_sport}:")
        print(f"  - {cat.display_name} ({cat.event_count} gold medals)")

    print(f"\nTotal gold medals: {sum(c.event_count for c in categories if not c.is_overall)}")
