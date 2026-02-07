"""
Wikipedia scraper for Winter Olympics 2026 medal results.

Fetches medal data from Wikipedia's MediaWiki API, cached for 30 minutes.
"""

import logging
import re
import requests
import streamlit as st
from datetime import datetime
from database import save_category_result, get_category_results, delete_category_result
from categories import get_all_categories

logger = logging.getLogger(__name__)

# IOC 3-letter codes to country names (matching events.py WINTER_OLYMPICS_COUNTRIES)
IOC_TO_COUNTRY = {
    "AUT": "Austria",
    "CAN": "Canada",
    "CHN": "China",
    "CRO": "Croatia",
    "CZE": "Czech Republic",
    "EST": "Estonia",
    "FIN": "Finland",
    "FRA": "France",
    "GER": "Germany",
    "HUN": "Hungary",
    "ISR": "Israel",
    "ITA": "Italy",
    "JAM": "Jamaica",
    "JPN": "Japan",
    "LAT": "Latvia",
    "LIE": "Liechtenstein",
    "NED": "Netherlands",
    "NOR": "Norway",
    "NZL": "New Zealand",
    "ROC": "ROC/Russia",
    "RUS": "ROC/Russia",
    "AIN": "Individual Neutral Athletes",
    "KOR": "South Korea",
    "SWE": "Sweden",
    "SUI": "Switzerland",
    "TPE": "Chinese Taipei",
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

# Flag emoji for common IOC codes
IOC_TO_FLAG = {
    "AUS": "\U0001f1e6\U0001f1fa", "AUT": "\U0001f1e6\U0001f1f9", "BEL": "\U0001f1e7\U0001f1ea",
    "BLR": "\U0001f1e7\U0001f1fe", "CAN": "\U0001f1e8\U0001f1e6", "CHN": "\U0001f1e8\U0001f1f3",
    "CRO": "\U0001f1ed\U0001f1f7", "CZE": "\U0001f1e8\U0001f1ff", "ESP": "\U0001f1ea\U0001f1f8",
    "EST": "\U0001f1ea\U0001f1ea", "FIN": "\U0001f1eb\U0001f1ee", "FRA": "\U0001f1eb\U0001f1f7",
    "GBR": "\U0001f1ec\U0001f1e7", "GER": "\U0001f1e9\U0001f1ea", "HUN": "\U0001f1ed\U0001f1fa",
    "ISR": "\U0001f1ee\U0001f1f1", "ITA": "\U0001f1ee\U0001f1f9", "JAM": "\U0001f1ef\U0001f1f2",
    "JPN": "\U0001f1ef\U0001f1f5", "KOR": "\U0001f1f0\U0001f1f7", "LAT": "\U0001f1f1\U0001f1fb",
    "LIE": "\U0001f1f1\U0001f1ee", "NED": "\U0001f1f3\U0001f1f1", "NOR": "\U0001f1f3\U0001f1f4",
    "NZL": "\U0001f1f3\U0001f1ff", "POL": "\U0001f1f5\U0001f1f1", "SLO": "\U0001f1f8\U0001f1ee",
    "SVK": "\U0001f1f8\U0001f1f0", "SUI": "\U0001f1e8\U0001f1ed", "SWE": "\U0001f1f8\U0001f1ea",
    "TPE": "\U0001f1f9\U0001f1fc", "UKR": "\U0001f1fa\U0001f1e6", "USA": "\U0001f1fa\U0001f1f8",
    "AIN": "\U0001f3f3\ufe0f",
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
        }, headers={"User-Agent": "OlympicsPredictionGame/1.0"}, timeout=10)
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


# ── New results-page scraper functions ──────────────────────────────────────

# Map Wikipedia sport section headers → our sport category IDs
_WIKI_SPORT_TO_ID = {
    "Alpine skiing": "alpine_skiing",
    "Biathlon": "biathlon",
    "Bobsleigh": "bobsled",
    "Cross-country skiing": "cross_country_skiing",
    "Curling": "curling",
    "Figure skating": "figure_skating",
    "Freestyle skiing": "freestyle_skiing",
    "Ice hockey": "ice_hockey",
    "Luge": "luge",
    "Nordic combined": "nordic_combined",
    "Short track speed skating": "short_track_speed_skating",
    "Skeleton": "skeleton",
    "Ski jumping": "ski_jumping",
    "Ski mountaineering": "ski_mountaineering",
    "Snowboarding": "snowboard",
    "Speed skating": "speed_skating",
}


@st.cache_data(ttl=1800)
def fetch_medal_table() -> list[dict]:
    """Fetch the overall medal table from Wikipedia (G/S/B/Total per country)."""
    wikitext = fetch_wiki_page("2026_Winter_Olympics_medal_table")
    if not wikitext:
        return []

    # Strip HTML comments to exclude commented-out entries (e.g. AIN)
    clean = re.sub(r'<!--.*?-->', '', wikitext, flags=re.DOTALL)

    countries: dict[str, dict] = {}
    for medal_type in ("gold", "silver", "bronze"):
        for match in re.finditer(rf'{medal_type}_([A-Z]{{3}})\s*=\s*(\d+)', clean):
            ioc = match.group(1)
            count = int(match.group(2))
            if ioc not in countries:
                countries[ioc] = {"ioc": ioc, "gold": 0, "silver": 0, "bronze": 0}
            countries[ioc][medal_type] = count

    result = []
    for ioc, data in countries.items():
        data["country"] = IOC_TO_COUNTRY.get(ioc, ioc)
        data["total"] = data["gold"] + data["silver"] + data["bronze"]
        if data["total"] > 0:
            result.append(data)

    # Sort: gold desc → silver desc → bronze desc
    result.sort(key=lambda r: (-r["gold"], -r["silver"], -r["bronze"]))
    return result


@st.cache_data(ttl=1800)
def fetch_all_medalists() -> list[dict]:
    """
    Fetch individual event medalists from Wikipedia.

    Returns list of dicts with keys:
      event, sport, gold_athlete, gold_country, silver_athlete, silver_country,
      bronze_athlete, bronze_country
    Only includes events where at least the gold medalist cell is populated.
    """
    wikitext = fetch_wiki_page("List_of_2026_Winter_Olympics_medal_winners")
    if not wikitext:
        return []

    results = []
    current_sport = None
    current_gender = None

    # Split into sections by == headers
    lines = wikitext.split('\n')

    for i, line in enumerate(lines):
        # Track sport sections (==Sport==)
        sport_match = re.match(r'^==([^=]+)==\s*$', line)
        if sport_match:
            current_sport = sport_match.group(1).strip()
            current_gender = None
            continue

        # Track gender sub-sections (===Men's events===)
        gender_match = re.match(r'^===([^=]+)===\s*$', line)
        if gender_match:
            gender_text = gender_match.group(1).strip()
            if "Men" in gender_text:
                current_gender = "Men"
            elif "Women" in gender_text:
                current_gender = "Women"
            elif "Mixed" in gender_text:
                current_gender = "Mixed"
            else:
                current_gender = None
            continue

    # Now parse event rows using the |-valign pattern
    # Split on event rows
    row_pattern = re.compile(r'\|-\s*valign\s*=\s*"top"')
    rows = row_pattern.split(wikitext)

    # Track current sport/gender as we go through the text
    current_sport = None
    current_gender = None

    for row in rows[1:]:  # Skip the first split (before any row)
        # Find where this row sits by checking preceding text for section headers
        # We need to find the position in the original text
        pass

    # Better approach: iterate through text sequentially
    current_sport = None
    current_gender = None
    # Split on lines that start event rows
    segments = re.split(r'\n\|-\s*valign\s*=\s*"top"\s*\n', wikitext)
    preamble = segments[0]  # Text before first event row

    # Extract sport/gender from preamble
    for m in re.finditer(r'^==([^=]+)==\s*$', preamble, re.MULTILINE):
        current_sport = m.group(1).strip()
    for m in re.finditer(r'^===([^=]+)===\s*$', preamble, re.MULTILINE):
        g = m.group(1).strip()
        if "Men" in g:
            current_gender = "Men"
        elif "Women" in g:
            current_gender = "Women"
        elif "Mixed" in g:
            current_gender = "Mixed"

    for segment in segments[1:]:
        # Check if this segment contains new section headers before the event data
        # Headers that appear before the next event pipe cell
        first_pipe = segment.find('|')
        header_region = segment[:first_pipe] if first_pipe > 0 else ""

        for m in re.finditer(r'^==([^=]+)==\s*$', header_region, re.MULTILINE):
            current_sport = m.group(1).strip()
        for m in re.finditer(r'^===([^=]+)===\s*$', header_region, re.MULTILINE):
            g = m.group(1).strip()
            if "Men" in g:
                current_gender = "Men"
            elif "Women" in g:
                current_gender = "Women"
            elif "Mixed" in g:
                current_gender = "Mixed"

        # Also check for headers that appear after a table end |}
        # and before the next event data in this segment
        for m in re.finditer(r'^==([^=]+)==\s*$', segment, re.MULTILINE):
            current_sport = m.group(1).strip()
        for m in re.finditer(r'^===([^=]+)===\s*$', segment, re.MULTILINE):
            g = m.group(1).strip()
            if "Men" in g:
                current_gender = "Men"
            elif "Women" in g:
                current_gender = "Women"
            elif "Mixed" in g:
                current_gender = "Mixed"

        # Extract event name from first cell: | EventName<br />...
        event_match = re.match(r'\s*\|\s*(.+?)(?:<br\s*/?>|\n)', segment)
        if not event_match:
            continue
        event_name = event_match.group(1).strip()
        # Clean up Nowrap templates: {{Nowrap|actual name}}
        event_name = re.sub(r'\{\{Nowrap\|([^}]+)\}\}', r'\1', event_name)
        # Remove any remaining wiki markup
        event_name = re.sub(r'\{\{[^}]*\}\}', '', event_name).strip()
        event_name = re.sub(r'\[\[([^|\]]*\|)?([^\]]+)\]\]', r'\2', event_name).strip()

        if not event_name or not current_sport:
            continue

        # Extract medal cells - look for flagIOCmedalist patterns
        medalist_matches = list(re.finditer(
            r'flagIOCmedalist\|\[\[([^\]|]+)(?:\|([^\]]+))?\]\]\|([A-Z]{3})',
            segment
        ))

        # Skip if no medalists at all (event not held yet)
        if not medalist_matches:
            continue

        # Build gender-qualified event name
        gender_prefix = f"{current_gender}'s " if current_gender else ""
        full_event = f"{gender_prefix}{event_name}"

        # Parse each medal position (gold=0, silver=1, bronze=2)
        # Split segment into pipe-delimited cells after the event name cell
        gold_athlete = gold_country = None
        silver_athlete = silver_country = None
        bronze_athlete = bronze_country = None

        # Find medal cells by splitting on top-level pipe delimiters
        # After the event name cell, there are 3 cells: gold | silver | bronze
        cells = re.split(r'\n\|', segment)
        # cells[0] is the event name cell, cells[1..3] are G/S/B
        for ci, cell in enumerate(cells[1:4], 1):
            m = re.search(
                r'flagIOCmedalist\|\[\[([^\]|]+)(?:\|([^\]]+))?\]\]\|([A-Z]{3})',
                cell
            )
            if m:
                raw_name = m.group(2) or m.group(1)  # display name or link target
                ioc = m.group(3)
                if ci == 1:
                    gold_athlete, gold_country = raw_name, ioc
                elif ci == 2:
                    silver_athlete, silver_country = raw_name, ioc
                elif ci == 3:
                    bronze_athlete, bronze_country = raw_name, ioc

        # Only include if at least gold is populated
        if gold_athlete:
            results.append({
                "event": full_event,
                "sport": current_sport,
                "gold_athlete": gold_athlete,
                "gold_country": gold_country,
                "silver_athlete": silver_athlete,
                "silver_country": silver_country or "",
                "bronze_athlete": bronze_athlete,
                "bronze_country": bronze_country or "",
            })

    return results


def get_medalist_summary() -> list[dict]:
    """
    Aggregate medalists by athlete: count G/S/B/Total across events.

    Returns sorted list of {"athlete", "country", "ioc", "gold", "silver", "bronze", "total"}.
    """
    all_medalists = fetch_all_medalists()
    athlete_map: dict[str, dict] = {}

    for row in all_medalists:
        for medal_type in ("gold", "silver", "bronze"):
            name = row.get(f"{medal_type}_athlete")
            ioc = row.get(f"{medal_type}_country")
            if name and ioc:
                key = f"{name}|{ioc}"
                if key not in athlete_map:
                    athlete_map[key] = {
                        "athlete": name,
                        "ioc": ioc,
                        "country": IOC_TO_COUNTRY.get(ioc, ioc),
                        "gold": 0, "silver": 0, "bronze": 0,
                    }
                athlete_map[key][medal_type] += 1

    result = list(athlete_map.values())
    for r in result:
        r["total"] = r["gold"] + r["silver"] + r["bronze"]

    result.sort(key=lambda r: (-r["total"], -r["gold"], r["athlete"]))
    return result


def fetch_sport_event_results(sport_name: str) -> dict[str, dict]:
    """
    Get individual event results for a sport.

    Args:
        sport_name: Wikipedia sport name (e.g. "Alpine skiing")

    Returns:
        Dict mapping event name → {"gold": "Country", "silver": "Country", "bronze": "Country"}
    """
    all_medalists = fetch_all_medalists()
    results = {}
    for row in all_medalists:
        if row["sport"] == sport_name:
            results[row["event"]] = {
                "gold": IOC_TO_COUNTRY.get(row["gold_country"], row["gold_country"]),
                "silver": IOC_TO_COUNTRY.get(row.get("silver_country", ""), row.get("silver_country", "")),
                "bronze": IOC_TO_COUNTRY.get(row.get("bronze_country", ""), row.get("bronze_country", "")),
            }
    return results


# Categories that need admin entry (scraper can't resolve these)
ADMIN_ONLY_CATEGORIES = {
    "prop_vonn_gold",
    "prop_usa_figure_skating_medals",
    "prop_most_individual_medals",
}


def _category_is_complete(category_id: str) -> bool:
    """Check if all events for a category have finished (last_event_date has passed)."""
    now = datetime.now()
    for cat in get_all_categories():
        if cat.id == category_id:
            if cat.last_event_date and cat.last_event_date < now:
                return True
            return False
    return False


def update_results_from_scraper():
    """
    Fetch Wikipedia data and update category results in the DB.
    Only saves results for categories whose last_event_date has passed,
    preventing premature results from partial data.
    Cleans up any previously saved premature results.
    Skips categories that need admin entry.
    """
    existing_results = get_category_results()

    # Sport-level categories: country with most golds
    for sport_id in SPORT_TO_WIKI_PAGE:
        if not _category_is_complete(sport_id):
            # Remove premature result if one was saved earlier
            if sport_id in existing_results:
                delete_category_result(sport_id)
            continue
        if sport_id in existing_results:
            continue
        leader = get_sport_gold_leader(sport_id)
        if leader:
            save_category_result(sport_id, leader)

    # Overall: country with most golds across all sports
    if not _category_is_complete("overall"):
        if "overall" in existing_results:
            delete_category_result("overall")
    elif "overall" not in existing_results:
        overall_leader = get_overall_gold_leader()
        if overall_leader:
            save_category_result("overall", overall_leader)

    # Featured: Men's Ice Hockey Gold
    hockey_cat_id = "featured_mens_ice_hockey_gold"
    if not _category_is_complete(hockey_cat_id):
        if hockey_cat_id in existing_results:
            delete_category_result(hockey_cat_id)
    elif hockey_cat_id not in existing_results:
        winner = get_event_gold_winner("ice_hockey", "Men")
        if winner:
            save_category_result(hockey_cat_id, winner)

    # Featured: Women's Figure Skating Singles country
    fs_cat_id = "prop_womens_figure_skating_country"
    if not _category_is_complete(fs_cat_id):
        if fs_cat_id in existing_results:
            delete_category_result(fs_cat_id)
    elif fs_cat_id not in existing_results:
        winner = get_event_gold_winner("figure_skating", "Women's Singles")
        if winner:
            save_category_result(fs_cat_id, winner)
