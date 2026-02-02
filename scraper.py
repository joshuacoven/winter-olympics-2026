"""
Wikipedia scraper for Winter Olympics 2026 medal results.

Fetches medal data from Wikipedia's MediaWiki API, cached for 30 minutes.
"""

import logging
import re
import requests
import streamlit as st
from database import save_category_result, get_category_results

logger = logging.getLogger(__name__)

# IOC 3-letter codes to country names (matching events.py WINTER_OLYMPICS_COUNTRIES)
IOC_TO_COUNTRY = {
    "AUT": "Austria",
    "CAN": "Canada",
    "CHN": "China",
    "CZE": "Czech Republic",
    "FIN": "Finland",
    "FRA": "France",
    "GER": "Germany",
    "ITA": "Italy",
    "JPN": "Japan",
    "NED": "Netherlands",
    "NOR": "Norway",
    "ROC": "ROC/Russia",
    "RUS": "ROC/Russia",
    "KOR": "South Korea",
    "SWE": "Sweden",
    "SUI": "Switzerland",
    "USA": "United States",
    "AUS": "Australia",
    "BLR": "Belarus",
    "BEL": "Belgium",
    "GBR": "Great Britain",
    "POL": "Poland",
    "SVK": "Slovakia",
    "SLO": "Slovenia",
    "ESP": "Spain",
    "UKR": "Ukraine",
}

# Map our sport category IDs to Wikipedia page names
SPORT_TO_WIKI_PAGE = {
    "alpine_skiing": "Alpine_skiing_at_the_2026_Winter_Olympics",
    "biathlon": "Biathlon_at_the_2026_Winter_Olympics",
    "bobsled": "Bobsled_at_the_2026_Winter_Olympics",
    "cross_country_skiing": "Cross-country_skiing_at_the_2026_Winter_Olympics",
    "curling": "Curling_at_the_2026_Winter_Olympics",
    "figure_skating": "Figure_skating_at_the_2026_Winter_Olympics",
    "freestyle_skiing": "Freestyle_skiing_at_the_2026_Winter_Olympics",
    "ice_hockey": "Ice_hockey_at_the_2026_Winter_Olympics",
    "luge": "Luge_at_the_2026_Winter_Olympics",
    "nordic_combined": "Nordic_combined_at_the_2026_Winter_Olympics",
    "short_track_speed_skating": "Short_track_speed_skating_at_the_2026_Winter_Olympics",
    "skeleton": "Skeleton_at_the_2026_Winter_Olympics",
    "ski_jumping": "Ski_jumping_at_the_2026_Winter_Olympics",
    "ski_mountaineering": "Ski_mountaineering_at_the_2026_Winter_Olympics",
    "snowboard": "Snowboarding_at_the_2026_Winter_Olympics",
    "speed_skating": "Speed_skating_at_the_2026_Winter_Olympics",
}

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"


@st.cache_data(ttl=1800)
def fetch_wiki_page(page_name: str) -> str | None:
    """Fetch wikitext for a Wikipedia page. Cached 30 minutes."""
    try:
        resp = requests.get(WIKI_API_URL, params={
            "action": "parse",
            "page": page_name,
            "prop": "wikitext",
            "format": "json",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "parse" in data and "wikitext" in data["parse"]:
            return data["parse"]["wikitext"]["*"]
    except Exception:
        logger.warning("Failed to fetch Wikipedia page: %s", page_name, exc_info=True)
    return None


def parse_gold_counts(wikitext: str) -> dict[str, int]:
    """
    Parse gold medal counts per country from wikitext.
    Looks for patterns like: gold_SUI = 5, | gold = 3 (with nearby country code)
    Also parses medal table templates.
    """
    gold_counts: dict[str, int] = {}

    # Pattern 1: | gold_XXX = N (common in medal table templates)
    for match in re.finditer(r'\|\s*gold[_ ]([A-Z]{3})\s*=\s*(\d+)', wikitext):
        ioc_code = match.group(1)
        count = int(match.group(2))
        country = IOC_TO_COUNTRY.get(ioc_code)
        if country and count > 0:
            gold_counts[country] = gold_counts.get(country, 0) + count

    # Pattern 2: Medal table rows like {{MedalCountry|NOC=XXX}} ... | N | ...
    # or rows with {{flagIOC|XXX|2026 Winter}} followed by numbers
    for match in re.finditer(
        r'(?:flagIOC\|([A-Z]{3})|NOC=([A-Z]{3})).*?\|\s*(\d+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+',
        wikitext, re.DOTALL
    ):
        ioc_code = match.group(1) or match.group(2)
        golds = int(match.group(3))
        country = IOC_TO_COUNTRY.get(ioc_code)
        if country and golds > 0 and country not in gold_counts:
            gold_counts[country] = golds

    return gold_counts


def parse_event_winner(wikitext: str, event_keyword: str) -> str | None:
    """
    Parse the gold medal winner for a specific event from wikitext.
    Looks for flagIOC patterns near the event keyword.
    Returns country name or None.
    """
    # Find section containing the event keyword
    # Look for flagIOCmedalist or flagIOC patterns near the keyword
    pattern = re.escape(event_keyword)
    section_match = re.search(
        pattern + r'.*?flagIOC(?:medalist)?\|[^|]*\|([A-Z]{3})',
        wikitext, re.DOTALL | re.IGNORECASE
    )
    if section_match:
        ioc_code = section_match.group(1)
        return IOC_TO_COUNTRY.get(ioc_code)

    # Alternative: look backwards from event keyword
    # Find all gold medalist patterns and match to events
    return None


def get_sport_gold_leader(sport_id: str) -> str | None:
    """Get the country with the most golds for a sport. Returns None if no data."""
    page_name = SPORT_TO_WIKI_PAGE.get(sport_id)
    if not page_name:
        return None

    wikitext = fetch_wiki_page(page_name)
    if not wikitext:
        return None

    gold_counts = parse_gold_counts(wikitext)
    if not gold_counts:
        return None

    # Return country(ies) with most golds (comma-separated if tied)
    max_golds = max(gold_counts.values())
    leaders = [c for c, g in gold_counts.items() if g == max_golds]
    return ",".join(leaders)


def get_overall_gold_leader() -> str | None:
    """Get the country with the most total golds across all sports."""
    total_golds: dict[str, int] = {}

    for sport_id, page_name in SPORT_TO_WIKI_PAGE.items():
        wikitext = fetch_wiki_page(page_name)
        if not wikitext:
            continue
        sport_golds = parse_gold_counts(wikitext)
        for country, count in sport_golds.items():
            total_golds[country] = total_golds.get(country, 0) + count

    if not total_golds:
        return None

    max_golds = max(total_golds.values())
    leaders = [c for c, g in total_golds.items() if g == max_golds]
    return ",".join(leaders)


def get_event_gold_winner(sport_id: str, event_keyword: str) -> str | None:
    """Get the gold medal winning country for a specific event."""
    page_name = SPORT_TO_WIKI_PAGE.get(sport_id)
    if not page_name:
        return None

    wikitext = fetch_wiki_page(page_name)
    if not wikitext:
        return None

    return parse_event_winner(wikitext, event_keyword)


# Categories that need admin entry (scraper can't resolve these)
ADMIN_ONLY_CATEGORIES = {
    "prop_vonn_gold",
    "prop_usa_figure_skating_medals",
    "prop_most_individual_medals",
}


def update_results_from_scraper():
    """
    Fetch Wikipedia data and update category results in the DB.
    Skips categories that already have results or need admin entry.
    """
    existing_results = get_category_results()

    # Sport-level categories: country with most golds
    for sport_id in SPORT_TO_WIKI_PAGE:
        if sport_id in existing_results:
            continue
        leader = get_sport_gold_leader(sport_id)
        if leader:
            save_category_result(sport_id, leader)

    # Overall: country with most golds across all sports
    if "overall" not in existing_results:
        overall_leader = get_overall_gold_leader()
        if overall_leader:
            save_category_result("overall", overall_leader)

    # Featured: Men's Ice Hockey Gold
    hockey_cat_id = "featured_mens_ice_hockey_gold"
    if hockey_cat_id not in existing_results:
        winner = get_event_gold_winner("ice_hockey", "Men")
        if winner:
            save_category_result(hockey_cat_id, winner)

    # Featured: Women's Figure Skating Singles country
    fs_cat_id = "prop_womens_figure_skating_country"
    if fs_cat_id not in existing_results:
        winner = get_event_gold_winner("figure_skating", "Women's Singles")
        if winner:
            save_category_result(fs_cat_id, winner)
