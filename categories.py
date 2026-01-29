"""
Prediction Categories for Winter Olympics 2026

Users predict which country wins the most gold medals in each sport,
plus featured individual events and an overall prediction.
"""

from dataclasses import dataclass, field
from datetime import datetime
from events import get_all_events, WINTER_OLYMPICS_COUNTRIES


# Featured events: (sport, event_name, gender, display_name)
FEATURED_EVENTS = [
    ("Ice Hockey", "Men's", "Men", "Men's Ice Hockey"),
    ("Ice Hockey", "Women's", "Women", "Women's Ice Hockey"),
    ("Snowboard", "Men's Halfpipe", "Men", "Men's Snowboard Halfpipe"),
    ("Snowboard", "Women's Halfpipe", "Women", "Women's Snowboard Halfpipe"),
    ("Figure Skating", "Men's Singles", "Men", "Men's Figure Skating"),
    ("Figure Skating", "Women's Singles", "Women", "Women's Figure Skating"),
    ("Alpine Skiing", "Women's Downhill", "Women", "Women's Downhill"),
]


@dataclass
class PredictionCategory:
    """Represents a category for prediction."""
    id: str              # e.g., "alpine_skiing" or "featured_mens_hockey"
    sport: str           # e.g., "Alpine Skiing"
    gender: str | None   # None for sport-level and Overall
    display_name: str    # e.g., "Alpine Skiing" or "Men's Ice Hockey"
    event_count: int     # Number of gold medals in this category
    first_event_date: datetime | None
    last_event_date: datetime | None
    is_featured: bool = False

    @property
    def is_overall(self) -> bool:
        """Check if this is the Overall category."""
        return self.gender is None and self.sport == "Overall"


def generate_categories() -> list[PredictionCategory]:
    """
    Generate all prediction categories:
    1. Sport-level categories (aggregated across genders)
    2. Featured individual event categories
    3. Overall category
    """
    events = get_all_events()

    # === SPORT-LEVEL CATEGORIES ===
    sport_map: dict[str, list] = {}
    for event in events:
        if event.sport not in sport_map:
            sport_map[event.sport] = []
        sport_map[event.sport].append(event)

    categories = []

    for sport in sorted(sport_map.keys()):
        event_list = sport_map[sport]
        cat_id = sport.lower().replace(' ', '_').replace('-', '_')

        first_date = min(e.first_round_date for e in event_list)
        last_date = max(e.gold_medal_date for e in event_list)

        categories.append(PredictionCategory(
            id=cat_id,
            sport=sport,
            gender=None,
            display_name=sport,
            event_count=len(event_list),
            first_event_date=first_date,
            last_event_date=last_date,
            is_featured=False,
        ))

    # === FEATURED EVENT CATEGORIES ===
    for sport, event_name, gender, display_name in FEATURED_EVENTS:
        # Find the matching event
        matching = [e for e in events if e.sport == sport and e.name == event_name and e.gender == gender]
        if not matching:
            continue
        event = matching[0]

        clean_name = display_name.lower().replace(" ", "_").replace("'", "")
        cat_id = f"featured_{clean_name}"

        categories.append(PredictionCategory(
            id=cat_id,
            sport=sport,
            gender=gender,
            display_name=display_name,
            event_count=1,
            first_event_date=event.first_round_date,
            last_event_date=event.gold_medal_date,
            is_featured=True,
        ))

    # === OVERALL CATEGORY ===
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
        last_event_date=last_overall,
        is_featured=False,
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
    """Get list of unique sports (excluding Overall and featured)."""
    categories = get_all_categories()
    sports = set(c.sport for c in categories if not c.is_overall and not c.is_featured)
    return sorted(sports)


def get_countries() -> list[str]:
    """Return list of countries for prediction dropdowns."""
    return WINTER_OLYMPICS_COUNTRIES


if __name__ == "__main__":
    categories = get_all_categories()

    sport_cats = [c for c in categories if not c.is_featured and not c.is_overall]
    featured_cats = [c for c in categories if c.is_featured]
    overall_cat = [c for c in categories if c.is_overall]

    print(f"Total categories: {len(categories)}")
    print(f"\nSport categories ({len(sport_cats)}):")
    for cat in sport_cats:
        print(f"  - {cat.display_name} ({cat.event_count} golds) [{cat.id}]")

    print(f"\nFeatured events ({len(featured_cats)}):")
    for cat in featured_cats:
        print(f"  - {cat.display_name} ({cat.event_count} gold) [{cat.id}]")

    print(f"\nOverall:")
    for cat in overall_cat:
        print(f"  - {cat.display_name} ({cat.event_count} golds) [{cat.id}]")

    print(f"\nTotal gold medals: {sum(c.event_count for c in sport_cats)}")
