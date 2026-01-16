"""
Winter Olympics 2026 Milano-Cortina Events Data

Contains all medal events with dates, times, and metadata.
Olympics run February 6-22, 2026.
Times are in Europe/Rome timezone (CET/UTC+1).
"""

from datetime import datetime
from dataclasses import dataclass
from typing import Literal

# Countries that commonly compete in Winter Olympics
WINTER_OLYMPICS_COUNTRIES = [
    "Austria", "Canada", "China", "Czech Republic", "Finland", "France",
    "Germany", "Italy", "Japan", "Netherlands", "Norway", "ROC/Russia",
    "South Korea", "Sweden", "Switzerland", "United States",
    "Australia", "Belarus", "Belgium", "Great Britain", "Poland",
    "Slovakia", "Slovenia", "Spain", "Ukraine"
]

# Gender type
Gender = Literal["Men", "Women", "Mixed"]


@dataclass
class Event:
    """Represents a single Olympic event."""
    sport: str
    name: str
    gender: Gender
    first_round_date: datetime  # When the event starts (qualifying, first round, etc.)
    gold_medal_date: datetime   # When the gold medal is awarded

    @property
    def event_id(self) -> str:
        """Unique identifier for the event."""
        return f"{self.sport} - {self.name}"

    @property
    def display_name(self) -> str:
        """Display name with gender."""
        return f"{self.name}"


# All events with schedule
# Times are approximate based on typical Olympic scheduling
EVENTS_DATA = [
    # Alpine Skiing (Feb 6-22) - Cortina d'Ampezzo
    Event("Alpine Skiing", "Men's Downhill", "Men",
          datetime(2026, 2, 7, 11, 0), datetime(2026, 2, 7, 11, 0)),
    Event("Alpine Skiing", "Men's Super-G", "Men",
          datetime(2026, 2, 8, 11, 0), datetime(2026, 2, 8, 11, 0)),
    Event("Alpine Skiing", "Men's Giant Slalom", "Men",
          datetime(2026, 2, 15, 10, 0), datetime(2026, 2, 15, 13, 30)),
    Event("Alpine Skiing", "Men's Slalom", "Men",
          datetime(2026, 2, 21, 10, 0), datetime(2026, 2, 21, 13, 30)),
    Event("Alpine Skiing", "Men's Combined", "Men",
          datetime(2026, 2, 12, 10, 0), datetime(2026, 2, 12, 14, 0)),
    Event("Alpine Skiing", "Women's Downhill", "Women",
          datetime(2026, 2, 10, 11, 0), datetime(2026, 2, 10, 11, 0)),
    Event("Alpine Skiing", "Women's Super-G", "Women",
          datetime(2026, 2, 9, 11, 0), datetime(2026, 2, 9, 11, 0)),
    Event("Alpine Skiing", "Women's Giant Slalom", "Women",
          datetime(2026, 2, 18, 10, 0), datetime(2026, 2, 18, 13, 30)),
    Event("Alpine Skiing", "Women's Slalom", "Women",
          datetime(2026, 2, 20, 10, 0), datetime(2026, 2, 20, 13, 30)),
    Event("Alpine Skiing", "Women's Combined", "Women",
          datetime(2026, 2, 11, 10, 0), datetime(2026, 2, 11, 14, 0)),
    Event("Alpine Skiing", "Mixed Team Parallel", "Mixed",
          datetime(2026, 2, 16, 10, 0), datetime(2026, 2, 16, 12, 0)),

    # Biathlon (Feb 8-22) - Anterselva
    Event("Biathlon", "Men's 10km Sprint", "Men",
          datetime(2026, 2, 8, 14, 30), datetime(2026, 2, 8, 14, 30)),
    Event("Biathlon", "Men's 20km Individual", "Men",
          datetime(2026, 2, 12, 14, 30), datetime(2026, 2, 12, 14, 30)),
    Event("Biathlon", "Men's 12.5km Pursuit", "Men",
          datetime(2026, 2, 10, 14, 30), datetime(2026, 2, 10, 14, 30)),
    Event("Biathlon", "Men's 15km Mass Start", "Men",
          datetime(2026, 2, 22, 12, 30), datetime(2026, 2, 22, 12, 30)),
    Event("Biathlon", "Men's 4x7.5km Relay", "Men",
          datetime(2026, 2, 14, 14, 30), datetime(2026, 2, 14, 14, 30)),
    Event("Biathlon", "Women's 7.5km Sprint", "Women",
          datetime(2026, 2, 9, 14, 30), datetime(2026, 2, 9, 14, 30)),
    Event("Biathlon", "Women's 15km Individual", "Women",
          datetime(2026, 2, 11, 14, 30), datetime(2026, 2, 11, 14, 30)),
    Event("Biathlon", "Women's 10km Pursuit", "Women",
          datetime(2026, 2, 11, 10, 0), datetime(2026, 2, 11, 10, 0)),
    Event("Biathlon", "Women's 12.5km Mass Start", "Women",
          datetime(2026, 2, 21, 12, 30), datetime(2026, 2, 21, 12, 30)),
    Event("Biathlon", "Women's 4x6km Relay", "Women",
          datetime(2026, 2, 17, 14, 30), datetime(2026, 2, 17, 14, 30)),
    Event("Biathlon", "Mixed Relay", "Mixed",
          datetime(2026, 2, 8, 10, 0), datetime(2026, 2, 8, 10, 0)),

    # Bobsled (Feb 14-22) - Cortina
    Event("Bobsled", "Two-Man", "Men",
          datetime(2026, 2, 14, 20, 0), datetime(2026, 2, 15, 20, 0)),
    Event("Bobsled", "Four-Man", "Men",
          datetime(2026, 2, 21, 9, 30), datetime(2026, 2, 22, 9, 30)),
    Event("Bobsled", "Women's Monobob", "Women",
          datetime(2026, 2, 16, 9, 30), datetime(2026, 2, 17, 9, 30)),
    Event("Bobsled", "Women's Two-Woman", "Women",
          datetime(2026, 2, 18, 20, 0), datetime(2026, 2, 19, 20, 0)),

    # Cross-Country Skiing (Feb 7-22) - Tesero
    Event("Cross-Country Skiing", "Men's Sprint", "Men",
          datetime(2026, 2, 11, 12, 0), datetime(2026, 2, 11, 14, 0)),
    Event("Cross-Country Skiing", "Men's Team Sprint", "Men",
          datetime(2026, 2, 19, 12, 0), datetime(2026, 2, 19, 14, 0)),
    Event("Cross-Country Skiing", "Men's 15km", "Men",
          datetime(2026, 2, 14, 12, 0), datetime(2026, 2, 14, 12, 0)),
    Event("Cross-Country Skiing", "Men's 30km Mass Start", "Men",
          datetime(2026, 2, 8, 12, 0), datetime(2026, 2, 8, 12, 0)),
    Event("Cross-Country Skiing", "Men's 50km", "Men",
          datetime(2026, 2, 22, 10, 0), datetime(2026, 2, 22, 10, 0)),
    Event("Cross-Country Skiing", "Men's 4x10km Relay", "Men",
          datetime(2026, 2, 16, 10, 0), datetime(2026, 2, 16, 10, 0)),
    Event("Cross-Country Skiing", "Women's Sprint", "Women",
          datetime(2026, 2, 11, 11, 0), datetime(2026, 2, 11, 13, 0)),
    Event("Cross-Country Skiing", "Women's Team Sprint", "Women",
          datetime(2026, 2, 19, 11, 0), datetime(2026, 2, 19, 13, 0)),
    Event("Cross-Country Skiing", "Women's 10km", "Women",
          datetime(2026, 2, 13, 12, 0), datetime(2026, 2, 13, 12, 0)),
    Event("Cross-Country Skiing", "Women's 20km Mass Start", "Women",
          datetime(2026, 2, 7, 12, 0), datetime(2026, 2, 7, 12, 0)),
    Event("Cross-Country Skiing", "Women's 30km", "Women",
          datetime(2026, 2, 21, 10, 0), datetime(2026, 2, 21, 10, 0)),
    Event("Cross-Country Skiing", "Women's 4x5km Relay", "Women",
          datetime(2026, 2, 15, 10, 0), datetime(2026, 2, 15, 10, 0)),

    # Curling (Feb 6-22) - Milan
    Event("Curling", "Men's", "Men",
          datetime(2026, 2, 10, 9, 0), datetime(2026, 2, 21, 14, 30)),
    Event("Curling", "Women's", "Women",
          datetime(2026, 2, 10, 9, 0), datetime(2026, 2, 20, 14, 30)),
    Event("Curling", "Mixed Doubles", "Mixed",
          datetime(2026, 2, 6, 20, 0), datetime(2026, 2, 10, 14, 30)),

    # Figure Skating (Feb 6-22) - Milan
    Event("Figure Skating", "Men's Singles", "Men",
          datetime(2026, 2, 10, 10, 0), datetime(2026, 2, 12, 18, 30)),
    Event("Figure Skating", "Women's Singles", "Women",
          datetime(2026, 2, 17, 10, 0), datetime(2026, 2, 19, 18, 30)),
    Event("Figure Skating", "Pairs", "Mixed",
          datetime(2026, 2, 7, 18, 30), datetime(2026, 2, 9, 18, 30)),
    Event("Figure Skating", "Ice Dance", "Mixed",
          datetime(2026, 2, 13, 10, 0), datetime(2026, 2, 15, 18, 30)),
    Event("Figure Skating", "Team Event", "Mixed",
          datetime(2026, 2, 6, 10, 0), datetime(2026, 2, 8, 18, 30)),

    # Freestyle Skiing (Feb 6-21) - Livigno & Bormio
    Event("Freestyle Skiing", "Men's Moguls", "Men",
          datetime(2026, 2, 7, 12, 0), datetime(2026, 2, 9, 12, 30)),
    Event("Freestyle Skiing", "Men's Aerials", "Men",
          datetime(2026, 2, 11, 19, 0), datetime(2026, 2, 14, 19, 30)),
    Event("Freestyle Skiing", "Men's Ski Cross", "Men",
          datetime(2026, 2, 19, 12, 0), datetime(2026, 2, 20, 12, 30)),
    Event("Freestyle Skiing", "Men's Halfpipe", "Men",
          datetime(2026, 2, 12, 10, 30), datetime(2026, 2, 14, 10, 30)),
    Event("Freestyle Skiing", "Men's Slopestyle", "Men",
          datetime(2026, 2, 8, 10, 30), datetime(2026, 2, 10, 10, 30)),
    Event("Freestyle Skiing", "Men's Big Air", "Men",
          datetime(2026, 2, 10, 18, 0), datetime(2026, 2, 11, 18, 0)),
    Event("Freestyle Skiing", "Women's Moguls", "Women",
          datetime(2026, 2, 6, 12, 0), datetime(2026, 2, 8, 12, 30)),
    Event("Freestyle Skiing", "Women's Aerials", "Women",
          datetime(2026, 2, 10, 19, 0), datetime(2026, 2, 13, 19, 30)),
    Event("Freestyle Skiing", "Women's Ski Cross", "Women",
          datetime(2026, 2, 18, 12, 0), datetime(2026, 2, 19, 12, 30)),
    Event("Freestyle Skiing", "Women's Halfpipe", "Women",
          datetime(2026, 2, 11, 10, 30), datetime(2026, 2, 13, 10, 30)),
    Event("Freestyle Skiing", "Women's Slopestyle", "Women",
          datetime(2026, 2, 7, 10, 30), datetime(2026, 2, 9, 10, 30)),
    Event("Freestyle Skiing", "Women's Big Air", "Women",
          datetime(2026, 2, 9, 18, 0), datetime(2026, 2, 10, 18, 0)),
    Event("Freestyle Skiing", "Mixed Team Aerials", "Mixed",
          datetime(2026, 2, 8, 19, 0), datetime(2026, 2, 8, 20, 30)),

    # Ice Hockey (Feb 6-22) - Milan
    Event("Ice Hockey", "Men's", "Men",
          datetime(2026, 2, 11, 12, 10), datetime(2026, 2, 22, 12, 10)),
    Event("Ice Hockey", "Women's", "Women",
          datetime(2026, 2, 6, 12, 10), datetime(2026, 2, 17, 12, 10)),

    # Luge (Feb 7-13) - Cortina
    Event("Luge", "Men's Singles", "Men",
          datetime(2026, 2, 7, 18, 0), datetime(2026, 2, 8, 20, 30)),
    Event("Luge", "Women's Singles", "Women",
          datetime(2026, 2, 9, 18, 0), datetime(2026, 2, 10, 20, 30)),
    Event("Luge", "Doubles", "Mixed",
          datetime(2026, 2, 11, 18, 30), datetime(2026, 2, 11, 20, 30)),
    Event("Luge", "Team Relay", "Mixed",
          datetime(2026, 2, 13, 18, 30), datetime(2026, 2, 13, 20, 0)),

    # Nordic Combined (Feb 9-17) - Tesero & Predazzo
    Event("Nordic Combined", "Men's Individual Normal Hill", "Men",
          datetime(2026, 2, 9, 10, 0), datetime(2026, 2, 9, 16, 0)),
    Event("Nordic Combined", "Men's Individual Large Hill", "Men",
          datetime(2026, 2, 13, 10, 0), datetime(2026, 2, 13, 16, 0)),
    Event("Nordic Combined", "Men's Team Large Hill", "Men",
          datetime(2026, 2, 17, 10, 0), datetime(2026, 2, 17, 16, 0)),

    # Short Track Speed Skating (Feb 7-16) - Milan
    Event("Short Track", "Men's 500m", "Men",
          datetime(2026, 2, 15, 18, 0), datetime(2026, 2, 16, 19, 30)),
    Event("Short Track", "Men's 1000m", "Men",
          datetime(2026, 2, 7, 18, 0), datetime(2026, 2, 10, 19, 30)),
    Event("Short Track", "Men's 1500m", "Men",
          datetime(2026, 2, 8, 18, 0), datetime(2026, 2, 9, 19, 30)),
    Event("Short Track", "Men's 5000m Relay", "Men",
          datetime(2026, 2, 10, 18, 0), datetime(2026, 2, 14, 19, 30)),
    Event("Short Track", "Women's 500m", "Women",
          datetime(2026, 2, 10, 18, 0), datetime(2026, 2, 12, 19, 30)),
    Event("Short Track", "Women's 1000m", "Women",
          datetime(2026, 2, 14, 18, 0), datetime(2026, 2, 16, 19, 30)),
    Event("Short Track", "Women's 1500m", "Women",
          datetime(2026, 2, 7, 18, 0), datetime(2026, 2, 8, 19, 30)),
    Event("Short Track", "Women's 3000m Relay", "Women",
          datetime(2026, 2, 9, 18, 0), datetime(2026, 2, 12, 19, 30)),
    Event("Short Track", "Mixed Team Relay", "Mixed",
          datetime(2026, 2, 7, 18, 0), datetime(2026, 2, 7, 20, 30)),

    # Skeleton (Feb 12-14) - Cortina
    Event("Skeleton", "Men's", "Men",
          datetime(2026, 2, 12, 9, 30), datetime(2026, 2, 13, 11, 30)),
    Event("Skeleton", "Women's", "Women",
          datetime(2026, 2, 13, 18, 0), datetime(2026, 2, 14, 20, 0)),

    # Ski Jumping (Feb 7-17) - Predazzo
    Event("Ski Jumping", "Men's Normal Hill", "Men",
          datetime(2026, 2, 8, 18, 0), datetime(2026, 2, 8, 19, 30)),
    Event("Ski Jumping", "Men's Large Hill", "Men",
          datetime(2026, 2, 12, 18, 0), datetime(2026, 2, 12, 19, 30)),
    Event("Ski Jumping", "Men's Team Large Hill", "Men",
          datetime(2026, 2, 14, 18, 0), datetime(2026, 2, 14, 19, 30)),
    Event("Ski Jumping", "Women's Normal Hill", "Women",
          datetime(2026, 2, 7, 18, 0), datetime(2026, 2, 7, 19, 30)),
    Event("Ski Jumping", "Mixed Team", "Mixed",
          datetime(2026, 2, 10, 18, 0), datetime(2026, 2, 10, 19, 30)),

    # Snowboard (Feb 6-21) - Livigno & Cortina
    Event("Snowboard", "Men's Halfpipe", "Men",
          datetime(2026, 2, 11, 9, 30), datetime(2026, 2, 13, 9, 30)),
    Event("Snowboard", "Men's Slopestyle", "Men",
          datetime(2026, 2, 7, 9, 30), datetime(2026, 2, 9, 9, 30)),
    Event("Snowboard", "Men's Big Air", "Men",
          datetime(2026, 2, 9, 18, 0), datetime(2026, 2, 10, 18, 0)),
    Event("Snowboard", "Men's Snowboard Cross", "Men",
          datetime(2026, 2, 18, 13, 0), datetime(2026, 2, 19, 13, 30)),
    Event("Snowboard", "Men's Parallel Giant Slalom", "Men",
          datetime(2026, 2, 20, 13, 0), datetime(2026, 2, 20, 14, 30)),
    Event("Snowboard", "Women's Halfpipe", "Women",
          datetime(2026, 2, 10, 9, 30), datetime(2026, 2, 12, 9, 30)),
    Event("Snowboard", "Women's Slopestyle", "Women",
          datetime(2026, 2, 6, 9, 30), datetime(2026, 2, 8, 9, 30)),
    Event("Snowboard", "Women's Big Air", "Women",
          datetime(2026, 2, 8, 18, 0), datetime(2026, 2, 9, 18, 0)),
    Event("Snowboard", "Women's Snowboard Cross", "Women",
          datetime(2026, 2, 17, 13, 0), datetime(2026, 2, 18, 13, 30)),
    Event("Snowboard", "Women's Parallel Giant Slalom", "Women",
          datetime(2026, 2, 20, 12, 0), datetime(2026, 2, 20, 13, 30)),
    Event("Snowboard", "Mixed Team Snowboard Cross", "Mixed",
          datetime(2026, 2, 21, 13, 0), datetime(2026, 2, 21, 14, 30)),

    # Speed Skating (Feb 8-21) - Baselga di Piné
    Event("Speed Skating", "Men's 500m", "Men",
          datetime(2026, 2, 12, 16, 0), datetime(2026, 2, 12, 17, 30)),
    Event("Speed Skating", "Men's 1000m", "Men",
          datetime(2026, 2, 14, 16, 0), datetime(2026, 2, 14, 17, 30)),
    Event("Speed Skating", "Men's 1500m", "Men",
          datetime(2026, 2, 11, 14, 30), datetime(2026, 2, 11, 16, 0)),
    Event("Speed Skating", "Men's 5000m", "Men",
          datetime(2026, 2, 9, 15, 0), datetime(2026, 2, 9, 17, 0)),
    Event("Speed Skating", "Men's 10000m", "Men",
          datetime(2026, 2, 15, 15, 0), datetime(2026, 2, 15, 17, 30)),
    Event("Speed Skating", "Men's Mass Start", "Men",
          datetime(2026, 2, 21, 15, 0), datetime(2026, 2, 21, 16, 0)),
    Event("Speed Skating", "Men's Team Pursuit", "Men",
          datetime(2026, 2, 16, 16, 0), datetime(2026, 2, 17, 17, 0)),
    Event("Speed Skating", "Women's 500m", "Women",
          datetime(2026, 2, 13, 16, 0), datetime(2026, 2, 13, 17, 30)),
    Event("Speed Skating", "Women's 1000m", "Women",
          datetime(2026, 2, 16, 13, 30), datetime(2026, 2, 16, 15, 0)),
    Event("Speed Skating", "Women's 1500m", "Women",
          datetime(2026, 2, 10, 14, 30), datetime(2026, 2, 10, 16, 0)),
    Event("Speed Skating", "Women's 3000m", "Women",
          datetime(2026, 2, 8, 15, 0), datetime(2026, 2, 8, 17, 0)),
    Event("Speed Skating", "Women's 5000m", "Women",
          datetime(2026, 2, 18, 15, 0), datetime(2026, 2, 18, 17, 0)),
    Event("Speed Skating", "Women's Mass Start", "Women",
          datetime(2026, 2, 21, 14, 0), datetime(2026, 2, 21, 15, 0)),
    Event("Speed Skating", "Women's Team Pursuit", "Women",
          datetime(2026, 2, 16, 14, 0), datetime(2026, 2, 17, 15, 30)),
]


def get_all_events() -> list[Event]:
    """Return all events."""
    return EVENTS_DATA


def get_events_by_sport() -> dict[str, list[Event]]:
    """Return events grouped by sport."""
    sports = {}
    for event in EVENTS_DATA:
        if event.sport not in sports:
            sports[event.sport] = []
        sports[event.sport].append(event)
    return sports


def get_sports() -> list[str]:
    """Return list of all sports."""
    return sorted(set(e.sport for e in EVENTS_DATA))


def get_countries() -> list[str]:
    """Return list of countries for prediction dropdowns."""
    return WINTER_OLYMPICS_COUNTRIES


def filter_events(
    events: list[Event],
    sport: str | None = None,
    gender: Gender | None = None
) -> list[Event]:
    """Filter events by sport and/or gender."""
    result = events
    if sport:
        result = [e for e in result if e.sport == sport]
    if gender:
        result = [e for e in result if e.gender == gender]
    return result


def sort_events_by_date(events: list[Event], by_gold_medal: bool = False) -> list[Event]:
    """Sort events by date (first round or gold medal)."""
    if by_gold_medal:
        return sorted(events, key=lambda e: e.gold_medal_date)
    return sorted(events, key=lambda e: e.first_round_date)


def get_mock_results() -> dict[str, str]:
    """
    Return mock results for demonstration purposes.
    In production, this would fetch from an Olympics API.
    Returns dict mapping event_id to winning country.
    """
    # Mock results - a few sample events with winners
    # This simulates what the API would return after events conclude
    return {
        # These are placeholder results for demo purposes
        # Real results would come from Olympics API
    }


def fetch_results_from_api() -> dict[str, str]:
    """
    Fetch real results from Olympics API.
    TODO: Implement when API is available.
    For now, returns mock results.
    """
    # Placeholder for future API integration
    # Example API endpoints to consider:
    # - Olympics.com official API
    # - ESPN API
    # - Sports data providers
    return get_mock_results()


if __name__ == "__main__":
    # Print summary for verification
    events = get_all_events()
    sports = get_events_by_sport()

    print(f"Total events: {len(events)}")
    print(f"Total sports: {len(sports)}")
    print("\nEvents per sport:")
    for sport, event_list in sports.items():
        print(f"  {sport}: {len(event_list)} events")

    print("\nGender breakdown:")
    men = len([e for e in events if e.gender == "Men"])
    women = len([e for e in events if e.gender == "Women"])
    mixed = len([e for e in events if e.gender == "Mixed"])
    print(f"  Men: {men}, Women: {women}, Mixed: {mixed}")
