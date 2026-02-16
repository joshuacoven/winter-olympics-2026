"""
Rooting logic for Winter Olympics Prediction Game.

Calculates what users should root for based on their predictions
and current medal standings.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from categories import get_all_categories, get_category_by_id, PredictionCategory, ANSWER_COUNTRY, ANSWER_YES_NO, ANSWER_NUMBER
from database import get_predictions_for_set, get_category_results, get_prediction_set
from events import get_all_events, Event
from scraper import fetch_sport_event_results, fetch_medal_table, fetch_all_medalists


@dataclass
class CategoryStanding:
    """Current medal standings for a prediction category."""
    category_id: str
    gold_counts: dict[str, int]  # country -> current gold count
    remaining_event_count: int
    completed_event_count: int
    is_complete: bool


@dataclass
class RootingInfo:
    """Information about what a user should root for in a category."""
    category_id: str
    category_display_name: str
    user_prediction: str
    current_leader: str | None  # Can be "Norway, Sweden" for ties
    user_is_leading: bool
    remaining_events: list[Event]
    scenarios: list[str]  # Human-readable descriptions
    is_possible: bool  # Can user still win?
    urgency: str  # "today", "this_week", "later"


def get_rooting_info_for_user(prediction_set_id: int) -> list[RootingInfo]:
    """Get rooting recommendations for a user's prediction set.

    Returns a list of RootingInfo sorted by urgency and next event date.
    Skips completed categories.
    """
    # Load user predictions
    user_predictions = get_predictions_for_set(prediction_set_id)
    if not user_predictions:
        return []

    # Load actual results
    category_results = get_category_results()

    rooting_info_list = []

    for category_id, user_prediction in user_predictions.items():
        # Debug logging
        import sys

        # Skip if category is complete
        if category_id in category_results:
            print(f"DEBUG: Skipping {category_id} - already complete", file=sys.stderr)
            continue

        category = get_category_by_id(category_id)
        if not category:
            print(f"DEBUG: Skipping {category_id} - category not found", file=sys.stderr)
            continue

        # Calculate current standing
        standing = calculate_category_standing(category)
        print(f"DEBUG: {category_id} - completed={standing.completed_event_count}, remaining={standing.remaining_event_count}", file=sys.stderr)

        # Skip if no events have started yet (nothing to root for yet)
        if standing.completed_event_count == 0:
            print(f"DEBUG: Skipping {category_id} - no events started", file=sys.stderr)
            continue

        # Check if prediction is still possible
        is_possible = is_prediction_still_possible(standing, user_prediction, category)

        # Get remaining events
        remaining_events = get_remaining_events_for_category(category, standing)
        print(f"DEBUG: {category_id} - has {len(remaining_events)} remaining events", file=sys.stderr)

        if not remaining_events and not standing.is_complete:
            # All events done but official result not entered yet
            print(f"DEBUG: Skipping {category_id} - all events done, waiting for official result", file=sys.stderr)
            continue

        # Generate scenarios
        scenarios = generate_scenarios(standing, user_prediction, category)

        # Determine current leader
        current_leader = None
        user_is_leading = False
        if standing.gold_counts:
            max_golds = max(standing.gold_counts.values())
            leaders = sorted(c for c, g in standing.gold_counts.items() if g == max_golds)
            current_leader = ", ".join(leaders)
            user_is_leading = user_prediction in leaders

        # Calculate urgency
        urgency = calculate_urgency(remaining_events)

        rooting_info_list.append(RootingInfo(
            category_id=category_id,
            category_display_name=category.display_name,
            user_prediction=user_prediction,
            current_leader=current_leader,
            user_is_leading=user_is_leading,
            remaining_events=remaining_events,
            scenarios=scenarios,
            is_possible=is_possible,
            urgency=urgency
        ))

    # Sort: urgent first (today, this_week), then by next event date
    urgency_order = {"today": 0, "this_week": 1, "later": 2}
    rooting_info_list.sort(
        key=lambda r: (
            urgency_order.get(r.urgency, 3),
            # Event dates are timezone-naive, so use naive datetime.max for consistency
            r.remaining_events[0].gold_medal_date if r.remaining_events else datetime.max
        )
    )

    return rooting_info_list


def calculate_category_standing(category: PredictionCategory) -> CategoryStanding:
    """Calculate current medal standings for a category."""
    gold_counts: dict[str, int] = {}
    completed_events = []

    # For sport categories: count golds from scraped results
    if not category.is_overall and not category.is_featured:
        sport_results = fetch_sport_event_results(category.sport)
        completed_events = list(sport_results.keys())

        for event_name, medals in sport_results.items():
            gold_country = medals.get("gold", "")
            if gold_country:
                # Handle tied medals (e.g., "Norway / Sweden")
                for country in gold_country.split(" / "):
                    country = country.strip()
                    if country:
                        gold_counts[country] = gold_counts.get(country, 0) + 1

    # For overall category: use total gold counts
    elif category.is_overall:
        medal_table = fetch_medal_table()
        for row in medal_table:
            country = row["country"]
            gold_counts[country] = row["gold"]

        # Use all medalists to count completed events
        all_medalists = fetch_all_medalists()
        completed_events = all_medalists

    # For featured events: check specific event results
    # (For now, we'll rely on database results for featured categories)
    else:
        # Featured categories are typically handled by admin entry
        # We don't have automatic detection for specific featured events yet
        pass

    completed_count = len(completed_events)
    remaining_count = category.event_count - completed_count
    is_complete = remaining_count <= 0

    return CategoryStanding(
        category_id=category.id,
        gold_counts=gold_counts,
        remaining_event_count=max(0, remaining_count),
        completed_event_count=completed_count,
        is_complete=is_complete
    )


def is_prediction_still_possible(standing: CategoryStanding, user_prediction: str, category: PredictionCategory) -> bool:
    """Check if a user's prediction can still win."""
    # If complete, check if user won
    if standing.is_complete:
        if not standing.gold_counts:
            return False
        max_golds = max(standing.gold_counts.values())
        user_golds = standing.gold_counts.get(user_prediction, 0)
        return user_golds == max_golds

    # If no remaining events, check current standing
    if standing.remaining_event_count == 0:
        if not standing.gold_counts:
            return False
        max_golds = max(standing.gold_counts.values())
        user_golds = standing.gold_counts.get(user_prediction, 0)
        return user_golds == max_golds

    # Otherwise: calculate best-case scenario
    # User wins all remaining events
    user_current = standing.gold_counts.get(user_prediction, 0)
    user_best_case = user_current + standing.remaining_event_count

    # Find current leader (excluding user)
    leader_golds = 0
    for country, golds in standing.gold_counts.items():
        if country != user_prediction and golds > leader_golds:
            leader_golds = golds

    # User can win if their best case >= current leader
    return user_best_case >= leader_golds


def get_remaining_events_for_category(category: PredictionCategory, standing: CategoryStanding) -> list[Event]:
    """Get list of remaining events for a category, sorted by date."""
    all_events = get_all_events()

    # For sport categories: filter by sport
    if not category.is_overall and not category.is_featured:
        sport_events = [e for e in all_events if e.sport == category.sport]

        # Get completed event names from scraper
        completed_results = fetch_sport_event_results(category.sport)
        completed_names = set(completed_results.keys())

        # Filter out completed events using fuzzy matching
        remaining = []
        for event in sport_events:
            matched = False
            for completed_name in completed_names:
                if _events_match(completed_name, event.name):
                    matched = True
                    break
            if not matched:
                remaining.append(event)

        return sorted(remaining, key=lambda e: e.gold_medal_date)

    # For overall category: show next 10 events across all sports
    elif category.is_overall:
        now = datetime.now(ZoneInfo("Europe/Rome"))
        future_events = []
        for e in all_events:
            event_date = e.gold_medal_date
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=ZoneInfo("Europe/Rome"))
            if event_date > now:
                future_events.append(e)
        return sorted(future_events, key=lambda e: e.gold_medal_date)[:10]

    # For featured events: return empty (admin-managed)
    else:
        return []


def generate_scenarios(standing: CategoryStanding, user_prediction: str, category: PredictionCategory) -> list[str]:
    """Generate human-readable scenario descriptions."""
    scenarios = []

    # Special handling for yes/no and number answer types
    if category.answer_type == ANSWER_YES_NO:
        if user_prediction.lower() == "yes":
            scenarios.append("🎯 Rooting for this to happen!")
        else:
            scenarios.append("🎯 Rooting for this NOT to happen!")
        return scenarios

    if category.answer_type == ANSWER_NUMBER:
        scenarios.append(f"🎯 Rooting for exactly {user_prediction} medals!")
        return scenarios

    # Country predictions
    if not standing.gold_counts:
        scenarios.append(f"🎯 Rooting for {user_prediction} to win gold medals!")
        return scenarios

    user_golds = standing.gold_counts.get(user_prediction, 0)
    max_golds = max(standing.gold_counts.values())
    leaders = sorted(c for c, g in standing.gold_counts.items() if g == max_golds)

    # User is leading
    if user_prediction in leaders:
        if len(leaders) == 1:
            # User is sole leader - calculate strategic info
            # Find second place gold count
            second_place_golds = 0
            second_place_countries = []
            for country, golds in standing.gold_counts.items():
                if country != user_prediction:
                    if golds > second_place_golds:
                        second_place_golds = golds
                        second_place_countries = [country]
                    elif golds == second_place_golds:
                        second_place_countries.append(country)

            lead = user_golds - second_place_golds

            # Check if clinched (second place can't catch up even if they win all remaining)
            # Note: Tying is winning, so >= not >
            second_best_case = second_place_golds + standing.remaining_event_count

            if user_golds >= second_best_case:
                # Clinched! Even if 2nd place wins all remaining, they can at best tie (which is a win for user)
                scenarios.append(f"🏆 **Clinched!** You've secured this category — no one can catch up.")
            elif standing.remaining_event_count == 0:
                # All events done, just waiting for official result
                scenarios.append(f"✅ **Leading by {lead}!** All events complete — waiting for official result.")
            else:
                # Calculate magic number (how many more golds to guarantee a win/tie)
                # User needs enough golds to at least TIE with 2nd place's best case (tie = win)
                magic_number = max(0, second_place_golds + standing.remaining_event_count - user_golds)

                # Special case: user is the only one with golds
                if not second_place_countries:
                    if magic_number == 0 or user_golds >= standing.remaining_event_count:
                        scenarios.append(f"✅ **Dominant!** Only country with golds so far — keep it up!")
                    else:
                        scenarios.append(f"✅ **Leading!** Only country with golds so far — win {magic_number} more to clinch.")
                else:
                    # Format runner-up string to handle ties nicely
                    if len(second_place_countries) == 1:
                        runner_up_str = second_place_countries[0]
                    elif len(second_place_countries) == 2:
                        runner_up_str = f"{second_place_countries[0]} and {second_place_countries[1]} (tied)"
                    else:
                        # 3+ countries tied
                        runner_up_str = ", ".join(second_place_countries[:-1]) + f", and {second_place_countries[-1]} (tied)"

                    if magic_number == 0:
                        # Edge case: already clinched (should be caught above, but just in case)
                        scenarios.append(f"✅ **Leading by {lead}!** You've got this!")
                    elif magic_number > standing.remaining_event_count:
                        # Can't clinch mathematically, just need to stay ahead (or tie!)
                        scenarios.append(f"✅ **Leading by {lead}** over {runner_up_str}. Stay ahead (or tie!) to win!")
                    elif magic_number == 1:
                        scenarios.append(f"✅ **Leading by {lead}** over {runner_up_str}. Win **1 more gold** to clinch.")
                    else:
                        scenarios.append(f"✅ **Leading by {lead}** over {runner_up_str}. Win **{magic_number} more golds** to clinch.")
        else:
            # Tied for lead (which is winning!)
            other_leaders = [c for c in leaders if c != user_prediction]
            if standing.remaining_event_count == 0:
                # All events done, tied = win
                scenarios.append(f"🤝 **Tied for lead with {', '.join(other_leaders)}!** You win! (Tie counts as a win)")
            else:
                # Still events left - can pull ahead or maintain tie
                scenarios.append(f"🤝 **Tied for lead with {', '.join(other_leaders)}!** You're winning — pull ahead or maintain the tie!")

    # User is behind but possible
    elif standing.remaining_event_count > 0:
        gap = max_golds - user_golds
        leader_str = leaders[0] if len(leaders) == 1 else f"{leaders[0]} (tied)"

        if gap == 1:
            scenarios.append(f"📈 Need {user_prediction} to win **1 more gold** than {leader_str}.")
        else:
            scenarios.append(f"📈 Need {user_prediction} to win **{gap} more golds** than {leader_str}.")

        # Add context about remaining events
        if standing.remaining_event_count <= gap:
            scenarios.append(f"⚠️ Only {standing.remaining_event_count} events left — need near-perfect results!")

    # Eliminated
    else:
        scenarios.append(f"❌ **Mathematically eliminated** — {leaders[0]} has too many golds.")

    return scenarios


def calculate_urgency(events: list[Event]) -> str:
    """Calculate urgency level based on next event timing."""
    if not events:
        return "later"

    next_event = events[0]
    now = datetime.now(ZoneInfo("Europe/Rome"))

    # Event dates are timezone-naive but represent Europe/Rome time
    # Localize the event date to Europe/Rome for comparison
    event_date = next_event.gold_medal_date
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=ZoneInfo("Europe/Rome"))

    # Today
    if event_date.date() == now.date():
        return "today"

    # Within 7 days
    if event_date <= now + timedelta(days=7):
        return "this_week"

    return "later"


def _normalize_event_name(name: str) -> str:
    """Normalize event name for comparison (same logic as app.py)."""
    import re
    n = name.lower()
    # Strip gender prefixes
    n = re.sub(r"^(men\'?s?|women\'?s?|mixed)\s*", "", n)
    # Normalize common abbreviations
    n = n.replace("kilometres", "km").replace("kilometre", "km").replace("metres", "m").replace("metre", "m")
    # Expand Olympics.com abbreviations
    n = re.sub(r'\bnh\b', 'normal hill', n)
    n = re.sub(r'\blh\b', 'large hill', n)
    # Remove spaces, punctuation
    n = re.sub(r'[^a-z0-9]', '', n)
    return n


def _event_type_keyword(name: str) -> str:
    """Extract event type keyword (letters only)."""
    return re.sub(r'[0-9]', '', _normalize_event_name(name))


def _extract_gender(name: str) -> str:
    """Extract gender prefix from event name."""
    low = name.lower()
    if low.startswith("women"):
        return "women"
    if low.startswith("men"):
        return "men"
    if low.startswith("mixed"):
        return "mixed"
    return ""


def _events_match(result_name: str, event_name: str) -> bool:
    """Check if a result event name matches an Event object name (fuzzy matching)."""
    if _extract_gender(result_name) != _extract_gender(event_name):
        return False

    result_norm = _normalize_event_name(result_name)
    event_norm = _normalize_event_name(event_name)

    # Strict: exact or substring match
    if result_norm == event_norm or result_norm in event_norm or event_norm in result_norm:
        return True

    # Fuzzy fallback: compare event type keywords
    result_kw = _event_type_keyword(result_name)
    event_kw = _event_type_keyword(event_name)
    if len(result_kw) >= 4 and len(event_kw) >= 4:
        if result_kw == event_kw or result_kw in event_kw or event_kw in result_kw:
            return True

    return False
