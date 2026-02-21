"""
Olympics.com scraper for Winter Olympics 2026 medal results.

Primary source: Olympics.com medals page (embedded JSON data).
Fallback: Wikipedia MediaWiki API.
Results are cached for 10 minutes via Streamlit.
"""

import logging
import re
import json
import subprocess
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from database import save_category_result, get_category_results, delete_category_result
from categories import get_all_categories

logger = logging.getLogger(__name__)

# Browser headers required by Olympics.com (blocks requests without these)
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

OLYMPICS_MEDALS_URL = "https://www.olympics.com/en/milano-cortina-2026/medals"
OLYMPICS_MEDALLISTS_URL = "https://www.olympics.com/en/milano-cortina-2026/medals/medallists"

# IOC 3-letter codes to country names (matching events.py WINTER_OLYMPICS_COUNTRIES)
# Only codes whose official IOC name differs from our display name need to be here.
# Unknown codes are auto-resolved via _resolve_ioc_code() from Olympics.com data.
IOC_TO_COUNTRY = {
    "AIN": "Individual Neutral Athletes",
    "ALB": "Albania",
    "AND": "Andorra",
    "ARG": "Argentina",
    "ARM": "Armenia",
    "AUS": "Australia",
    "AUT": "Austria",
    "AZE": "Azerbaijan",
    "BEL": "Belgium",
    "BEN": "Benin",
    "BIH": "Bosnia and Herzegovina",
    "BLR": "Belarus",
    "BOL": "Bolivia",
    "BRA": "Brazil",
    "BUL": "Bulgaria",
    "CAN": "Canada",
    "CHI": "Chile",
    "CHN": "China",
    "COL": "Colombia",
    "CRO": "Croatia",
    "CYP": "Cyprus",
    "CZE": "Czech Republic",
    "DEN": "Denmark",
    "ECU": "Ecuador",
    "ERI": "Eritrea",
    "ESP": "Spain",
    "EST": "Estonia",
    "FIN": "Finland",
    "FRA": "France",
    "GBR": "Great Britain",
    "GEO": "Georgia",
    "GER": "Germany",
    "GRE": "Greece",
    "GBS": "Guinea-Bissau",
    "HAI": "Haiti",
    "HKG": "Hong Kong",
    "HUN": "Hungary",
    "ICE": "Iceland",  # IOC code ISL also used
    "IND": "India",
    "IRI": "Iran",
    "IRL": "Ireland",
    "ISL": "Iceland",
    "ISR": "Israel",
    "ITA": "Italy",
    "JAM": "Jamaica",
    "JPN": "Japan",
    "KAZ": "Kazakhstan",
    "KEN": "Kenya",
    "KOS": "Kosovo",
    "KGZ": "Kyrgyzstan",
    "KOR": "South Korea",
    "LAT": "Latvia",
    "LBN": "Lebanon",
    "LIE": "Liechtenstein",
    "LTU": "Lithuania",
    "LUX": "Luxembourg",
    "MAD": "Madagascar",
    "MAS": "Malaysia",
    "MLT": "Malta",
    "MEX": "Mexico",
    "MDA": "Moldova",
    "MON": "Monaco",
    "MGL": "Mongolia",
    "MNE": "Montenegro",
    "MAR": "Morocco",
    "NED": "Netherlands",
    "NOR": "Norway",
    "NZL": "New Zealand",
    "NGR": "Nigeria",
    "MKD": "North Macedonia",
    "PAK": "Pakistan",
    "PHI": "Philippines",
    "POL": "Poland",
    "POR": "Portugal",
    "PUR": "Puerto Rico",
    "ROC": "ROC/Russia",
    "ROU": "Romania",
    "RUS": "ROC/Russia",
    "SMR": "San Marino",
    "KSA": "Saudi Arabia",
    "SRB": "Serbia",
    "SGP": "Singapore",
    "SVK": "Slovakia",
    "SLO": "Slovenia",
    "RSA": "South Africa",
    "SUI": "Switzerland",
    "SWE": "Sweden",
    "THA": "Thailand",
    "TPE": "Chinese Taipei",
    "TTO": "Trinidad and Tobago",
    "TUR": "Turkey",
    "UAE": "United Arab Emirates",
    "UKR": "Ukraine",
    "URU": "Uruguay",
    "USA": "United States",
    "UZB": "Uzbekistan",
    "VEN": "Venezuela",
}

# Runtime cache for IOC codes discovered from Olympics.com data
_ioc_cache: dict[str, str] = {}


def _resolve_ioc_code(ioc: str) -> str:
    """Resolve an IOC code to a country name.

    Checks the static mapping first, then a runtime cache populated from
    Olympics.com data. Falls back to the raw IOC code as a last resort.
    """
    if ioc in IOC_TO_COUNTRY:
        return IOC_TO_COUNTRY[ioc]
    if ioc in _ioc_cache:
        return _ioc_cache[ioc]
    return ioc


def _learn_ioc_code(ioc: str, description: str):
    """Cache an IOC-to-country mapping discovered at runtime from Olympics.com."""
    if ioc and description and ioc not in IOC_TO_COUNTRY and ioc not in _ioc_cache:
        _ioc_cache[ioc] = description
        logger.info("Learned new IOC code: %s -> %s", ioc, description)

# IOC code → ISO 3166-1 alpha-2 code (for generating flag emojis programmatically).
# Only codes where IOC differs from ISO alpha-2 need to be listed here.
# Codes that match (e.g. "FR" for France) are auto-derived.
_IOC_TO_ISO2 = {
    "AIN": None,  # Individual Neutral Athletes - no country flag
    "BIH": "BA", "BUL": "BG", "CHI": "CL", "CRO": "HR", "CZE": "CZ",
    "DEN": "DK", "ESP": "ES", "GBR": "GB", "GBS": "GW", "GER": "DE",
    "GRE": "GR", "HAI": "HT", "HKG": "HK", "ICE": "IS", "IRI": "IR",
    "IRL": "IE", "KGZ": "KG", "KOR": "KR", "KOS": "XK", "KSA": "SA",
    "LAT": "LV", "LBN": "LB", "LIE": "LI", "LTU": "LT", "LUX": "LU",
    "MAD": "MG", "MAS": "MY", "MEX": "MX", "MDA": "MD", "MGL": "MN",
    "MKD": "MK", "MLT": "MT", "MNE": "ME", "MON": "MC", "MAR": "MA",
    "NED": "NL", "NGR": "NG", "NOR": "NO", "PHI": "PH", "POR": "PT",
    "PUR": "PR", "ROC": "RU", "ROU": "RO", "RSA": "ZA", "RUS": "RU",
    "SGP": "SG", "SLO": "SI", "SMR": "SM", "SRB": "RS", "SUI": "CH",
    "SVK": "SK", "THA": "TH", "TPE": "TW", "TTO": "TT", "TUR": "TR",
    "UAE": "AE", "URU": "UY", "UZB": "UZ", "VEN": "VE",
}


def ioc_to_flag(ioc: str) -> str:
    """Generate a flag emoji from an IOC code.

    Uses IOC→ISO alpha-2 mapping to programmatically generate the Unicode
    regional indicator flag emoji. Falls back to empty string for unknown codes
    or special entries (e.g. AIN/Individual Neutral Athletes gets white flag).
    """
    if ioc == "AIN":
        return "\U0001f3f3\ufe0f"  # white flag

    # Look up ISO alpha-2, or derive it from IOC code (works when they match)
    iso2 = _IOC_TO_ISO2.get(ioc)
    if iso2 is None and ioc not in _IOC_TO_ISO2:
        # Not in override map — try using first 2 chars of IOC code as ISO alpha-2
        iso2 = ioc[:2]

    if not iso2:
        return ""

    # Convert ISO alpha-2 to regional indicator symbols (flag emoji)
    try:
        return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso2.upper())
    except (ValueError, TypeError):
        return ""


# Build IOC_TO_FLAG dict for backward compatibility (used by app.py imports)
IOC_TO_FLAG = {ioc: ioc_to_flag(ioc) for ioc in IOC_TO_COUNTRY}

# Olympics.com discipline codes → our sport category IDs
_DISCIPLINE_TO_SPORT_ID = {
    "ALP": "alpine_skiing",
    "BTH": "biathlon",
    "BOB": "bobsled",
    "CCS": "cross_country_skiing",
    "CUR": "curling",
    "FSK": "figure_skating",
    "FRS": "freestyle_skiing",
    "IHO": "ice_hockey",
    "LUG": "luge",
    "NCB": "nordic_combined",
    "STK": "short_track_speed_skating",
    "SKN": "skeleton",
    "SJP": "ski_jumping",
    "SKM": "ski_mountaineering",
    "SBD": "snowboard",
    "SSK": "speed_skating",
}

# Our sport category IDs → display names used in the app
_SPORT_ID_TO_NAME = {
    "alpine_skiing": "Alpine Skiing",
    "biathlon": "Biathlon",
    "bobsled": "Bobsled",
    "cross_country_skiing": "Cross-Country Skiing",
    "curling": "Curling",
    "figure_skating": "Figure Skating",
    "freestyle_skiing": "Freestyle Skiing",
    "ice_hockey": "Ice Hockey",
    "luge": "Luge",
    "nordic_combined": "Nordic Combined",
    "short_track_speed_skating": "Short Track Speed Skating",
    "skeleton": "Skeleton",
    "ski_jumping": "Ski Jumping",
    "ski_mountaineering": "Ski Mountaineering",
    "snowboard": "Snowboard",
    "speed_skating": "Speed Skating",
}

# Map Wikipedia sport section headers → our sport category IDs (kept for app.py compatibility)
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


# ── Olympics.com data fetching ─────────────────────────────────────────────


def _curl_fetch(url: str, timeout: int = 20) -> str | None:
    """
    Fetch a URL using curl subprocess. More reliable than Python requests
    for sites with bot detection (e.g. Olympics.com uses Akamai which
    fingerprints the TLS stack and blocks Python requests).
    """
    try:
        result = subprocess.run(
            [
                "curl", "-sL",
                "--max-time", str(timeout),
                "-H", f"User-Agent: {_BROWSER_HEADERS['User-Agent']}",
                "-H", f"Accept: {_BROWSER_HEADERS['Accept']}",
                "-H", f"Accept-Language: {_BROWSER_HEADERS['Accept-Language']}",
                "-H", "Accept-Encoding: identity",
                "-H", "Sec-Fetch-Dest: document",
                "-H", "Sec-Fetch-Mode: navigate",
                "-H", "Sec-Fetch-Site: none",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        logger.warning("curl failed for %s: returncode=%d", url, result.returncode)
    except Exception:
        logger.warning("curl subprocess failed for %s", url, exc_info=True)
    return None


@st.cache_data(ttl=600)
def _fetch_olympics_medal_data() -> dict | None:
    """
    Fetch the Olympics.com medals page and extract embedded JSON medal data.
    Cached for 10 minutes. Returns the medalStandings dict or None on failure.
    """
    try:
        html = _curl_fetch(OLYMPICS_MEDALS_URL)
        if not html:
            return None

        # Find the embedded medalStandings JSON
        start = html.find('"medalStandings"')
        if start < 0:
            logger.warning("Could not find medalStandings in Olympics.com HTML")
            return None

        # Extract the JSON object after "medalStandings":
        colon = html.index(':', start)
        brace_start = html.index('{', colon)
        depth = 0
        pos = brace_start
        while pos < len(html):
            if html[pos] == '{':
                depth += 1
            elif html[pos] == '}':
                depth -= 1
                if depth == 0:
                    break
            pos += 1

        json_str = html[brace_start:pos + 1]
        data = json.loads(json_str)
        return data

    except Exception:
        logger.warning("Failed to fetch Olympics.com medal data", exc_info=True)
        return None


# ── Public API functions (used by app.py) ──────────────────────────────────


@st.cache_data(ttl=600)
def fetch_medal_table() -> list[dict]:
    """
    Fetch the overall medal table (G/S/B/Total per country).
    Returns list of dicts sorted by gold desc.
    """
    data = _fetch_olympics_medal_data()
    if not data:
        return []

    result = []
    for entry in data.get("medalsTable", []):
        ioc = entry.get("organisation", "")
        # Medal counts are in the medalsNumber array; find the "Total" entry
        medals = {m["type"]: m for m in entry.get("medalsNumber", [])}
        totals = medals.get("Total", {})
        gold = totals.get("gold", 0)
        silver = totals.get("silver", 0)
        bronze = totals.get("bronze", 0)
        total = totals.get("total", 0)

        # Learn IOC codes from the description field
        _learn_ioc_code(ioc, entry.get("description", ""))

        if total > 0:
            result.append({
                "ioc": ioc,
                "country": _resolve_ioc_code(ioc),
                "gold": gold,
                "silver": silver,
                "bronze": bronze,
                "total": total,
            })

    result.sort(key=lambda r: (-r["gold"], -r["silver"], -r["bronze"]))
    return result


@st.cache_data(ttl=600)
def fetch_all_medalists() -> list[dict]:
    """
    Fetch individual event medalists from Olympics.com.

    Returns list of dicts with keys:
      event, sport, gold_athlete, gold_country, silver_athlete, silver_country,
      bronze_athlete, bronze_country
    """
    data = _fetch_olympics_medal_data()
    if not data:
        return []

    # Collect all medal winners grouped by event
    # Each medal type stores lists to handle ties (e.g. two teams tie for silver)
    event_medals: dict[str, dict] = {}  # key = eventCode

    for entry in data.get("medalsTable", []):
        for disc in entry.get("disciplines", []):
            disc_code = disc.get("code", "")
            disc_name = disc.get("name", "")
            sport_id = _DISCIPLINE_TO_SPORT_ID.get(disc_code, disc_code)
            sport_display = _SPORT_ID_TO_NAME.get(sport_id, disc_name)

            for winner in disc.get("medalWinners", []):
                event_code = winner.get("eventCode", "")
                event_desc = winner.get("eventDescription", "")
                medal_type = winner.get("medalType", "")
                athlete = winner.get("competitorDisplayTvName", "")
                ioc = winner.get("organisation", "")

                if event_code not in event_medals:
                    event_medals[event_code] = {
                        "event": event_desc,
                        "sport": sport_display,
                        "gold_athletes": [], "gold_countries": [],
                        "silver_athletes": [], "silver_countries": [],
                        "bronze_athletes": [], "bronze_countries": [],
                    }

                row = event_medals[event_code]
                if medal_type == "ME_GOLD":
                    row["gold_athletes"].append(athlete)
                    row["gold_countries"].append(ioc)
                elif medal_type == "ME_SILVER":
                    row["silver_athletes"].append(athlete)
                    row["silver_countries"].append(ioc)
                elif medal_type == "ME_BRONZE":
                    row["bronze_athletes"].append(athlete)
                    row["bronze_countries"].append(ioc)

    # Flatten to single values for backward compatibility, joining ties with " / "
    results = []
    for row in event_medals.values():
        if not row["gold_athletes"]:
            continue
        results.append({
            "event": row["event"],
            "sport": row["sport"],
            "gold_athlete": " / ".join(row["gold_athletes"]),
            "gold_country": row["gold_countries"][0] if row["gold_countries"] else "",
            "silver_athlete": " / ".join(row["silver_athletes"]),
            "silver_country": " / ".join(row["silver_countries"]),
            "bronze_athlete": " / ".join(row["bronze_athletes"]),
            "bronze_country": " / ".join(row["bronze_countries"]),
        })
    return results


@st.cache_data(ttl=600)
def _fetch_medallists_data() -> list[dict] | None:
    """
    Fetch the Olympics.com medallists page and extract individual athlete data.
    This page lists every medalist individually, including team members.
    Cached for 10 minutes.
    """
    try:
        html = _curl_fetch(OLYMPICS_MEDALLISTS_URL)
        if not html:
            return None

        # Data is embedded in a script tag as JSON containing result_medallists_data
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for script in scripts:
            script = script.strip()
            if not script.startswith('{'):
                continue
            try:
                data = json.loads(script)
                if "result_medallists_data" in data:
                    athletes = (
                        data["result_medallists_data"]
                        .get("initialMedallist", {})
                        .get("athletes", [])
                    )
                    if athletes:
                        return athletes
            except (json.JSONDecodeError, KeyError):
                continue

        logger.warning("Could not find medallists data in Olympics.com HTML")
        return None
    except Exception:
        logger.warning("Failed to fetch Olympics.com medallists data", exc_info=True)
        return None


def get_medalist_summary() -> list[dict]:
    """
    Get individual medalist summary from the Olympics.com medallists page.
    Lists every athlete individually, including team members.

    Returns sorted list of {"athlete", "country", "ioc", "gold", "silver", "bronze", "total"}.
    """
    athletes = _fetch_medallists_data()
    if not athletes:
        # Fallback to aggregating from medal standings page
        return _get_medalist_summary_fallback()

    result = []
    for a in athletes:
        ioc = a.get("organisation", "")
        _learn_ioc_code(ioc, a.get("organisationName", ""))
        result.append({
            "athlete": a.get("tvName", a.get("fullName", "")),
            "ioc": ioc,
            "country": _resolve_ioc_code(ioc),
            "gold": a.get("medalsGold", 0),
            "silver": a.get("medalsSilver", 0),
            "bronze": a.get("medalsBronze", 0),
            "total": a.get("medalsTotal", 0),
        })

    result.sort(key=lambda r: (-r["total"], -r["gold"], r["athlete"]))
    return result


def _get_medalist_summary_fallback() -> list[dict]:
    """
    Fallback: aggregate medalists from the medals standings page.
    Does not include individual team members.
    """
    all_medalists = fetch_all_medalists()
    athlete_map: dict[str, dict] = {}

    for row in all_medalists:
        for medal_type in ("gold", "silver", "bronze"):
            name = row.get(f"{medal_type}_athlete")
            ioc = row.get(f"{medal_type}_country")
            if name and ioc:
                # Skip entries with " / " (tied countries) for clean athlete display
                if " / " in ioc:
                    continue
                key = f"{name}|{ioc}"
                if key not in athlete_map:
                    athlete_map[key] = {
                        "athlete": name,
                        "ioc": ioc,
                        "country": _resolve_ioc_code(ioc),
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
        sport_name: Display sport name (e.g. "Alpine Skiing") or
                    Wikipedia section name (e.g. "Alpine skiing") for compatibility.

    Returns:
        Dict mapping event name → {"gold": "Country", "silver": "Country", "bronze": "Country"}
    """
    # Normalize sport name for matching
    sport_lower = sport_name.lower().strip()

    all_medalists = fetch_all_medalists()
    results = {}
    for row in all_medalists:
        if row["sport"].lower().strip() == sport_lower:
            # Handle tied medals (countries joined with " / ")
            def _resolve_countries(raw: str) -> str:
                parts = [p.strip() for p in raw.split("/") if p.strip()]
                return " / ".join(_resolve_ioc_code(p) for p in parts)

            results[row["event"]] = {
                "gold": _resolve_countries(row.get("gold_country", "")),
                "silver": _resolve_countries(row.get("silver_country", "")),
                "bronze": _resolve_countries(row.get("bronze_country", "")),
            }
    return results


# ── Category result auto-update ────────────────────────────────────────────


# Categories that need admin entry (scraper can't resolve these)
ADMIN_ONLY_CATEGORIES = {
    "prop_vonn_gold",
    "prop_most_individual_medals",
}


def _category_is_complete(category_id: str) -> bool:
    """Check if all events for a category have finished.

    Uses last_event_date as primary check, but also considers a sport
    complete if the scraper already has results for all its events
    (handles schedule changes where events finish earlier than expected).
    """
    rome_tz = ZoneInfo("Europe/Rome")
    now = datetime.now(rome_tz).replace(tzinfo=None)
    for cat in get_all_categories():
        if cat.id == category_id:
            if cat.last_event_date and cat.last_event_date < now:
                return True
            # Fallback: check if scraper has all event results for this sport
            sport_display = _SPORT_ID_TO_NAME.get(category_id)
            if sport_display and cat.event_count > 0:
                sport_results = fetch_sport_event_results(sport_display)
                if len(sport_results) >= cat.event_count:
                    return True
            return False
    return False


def _get_sport_gold_leader_from_data(sport_id: str) -> str | None:
    """Get the country with the most golds for a sport from Olympics.com data."""
    data = _fetch_olympics_medal_data()
    if not data:
        return None

    # Find the discipline code for this sport
    disc_code = None
    for code, sid in _DISCIPLINE_TO_SPORT_ID.items():
        if sid == sport_id:
            disc_code = code
            break

    if not disc_code:
        return None

    # Count golds per country for this discipline
    gold_counts: dict[str, int] = {}
    for entry in data.get("medalsTable", []):
        for disc in entry.get("disciplines", []):
            if disc.get("code") == disc_code:
                golds = disc.get("gold", 0)
                if golds > 0:
                    ioc = entry.get("organisation", "")
                    country = _resolve_ioc_code(ioc)
                    gold_counts[country] = gold_counts.get(country, 0) + golds

    # Fallback: if medal standings don't have this discipline, count from medalists
    if not gold_counts:
        sport_display = _SPORT_ID_TO_NAME.get(sport_id)
        if sport_display:
            event_results = fetch_sport_event_results(sport_display)
            for _evt, medals in event_results.items():
                gold_country = medals.get("gold", "")
                if gold_country:
                    # Handle ties ("Country A / Country B")
                    for c in gold_country.split(" / "):
                        c = c.strip()
                        if c:
                            gold_counts[c] = gold_counts.get(c, 0) + 1

    if not gold_counts:
        return None

    max_golds = max(gold_counts.values())
    leaders = sorted(c for c, g in gold_counts.items() if g == max_golds)
    return ",".join(leaders)


def _get_overall_gold_leader_from_data() -> str | None:
    """Get the country with the most total golds across all sports."""
    medal_table = fetch_medal_table()
    if not medal_table:
        return None

    max_golds = medal_table[0]["gold"]  # Already sorted by gold desc
    leaders = sorted(r["country"] for r in medal_table if r["gold"] == max_golds)
    return ",".join(leaders)


def _get_event_winner_from_data(sport_id: str, event_keyword: str) -> str | None:
    """Get the gold medal winning country for a specific event."""
    all_medalists = fetch_all_medalists()
    sport_display = _SPORT_ID_TO_NAME.get(sport_id, "")
    keyword_lower = event_keyword.lower()

    for row in all_medalists:
        if row["sport"] == sport_display and keyword_lower in row["event"].lower():
            ioc = row["gold_country"]
            return _resolve_ioc_code(ioc)
    return None


def _get_usa_figure_skating_medal_count() -> str | None:
    """Count total medals (gold+silver+bronze) won by USA in Figure Skating."""
    results = fetch_sport_event_results("Figure Skating")
    if not results:
        return None
    count = 0
    for _evt, medals in results.items():
        for medal_type in ("gold", "silver", "bronze"):
            countries = medals.get(medal_type, "")
            if "United States" in countries:
                count += 1
    return str(count)


def _get_most_individual_medals_leader() -> str | None:
    """Get the country of the athlete(s) with the most total medals."""
    summary = get_medalist_summary()
    if not summary:
        return None

    # summary is sorted by (-total, -gold, athlete)
    max_total = summary[0]["total"]
    leaders = sorted(set(r["country"] for r in summary if r["total"] == max_total))
    return ",".join(leaders)


def get_projected_leaders() -> dict[str, list[str]]:
    """
    Get projected winners for all categories based on current leaders.
    For finished categories, returns the actual result.
    For unfinished categories, returns whoever is currently leading.
    Returns dict of category_id -> list of projected winners.
    """
    results = get_category_results()
    projected = dict(results)  # Start with actual results

    for cat in get_all_categories():
        if cat.id in projected:
            continue  # Already have actual result

        leader = None
        if cat.id in _DISCIPLINE_TO_SPORT_ID.values():
            leader = _get_sport_gold_leader_from_data(cat.id)
        elif cat.id == "overall":
            leader = _get_overall_gold_leader_from_data()
        elif cat.id == "featured_mens_ice_hockey_gold":
            leader = _get_event_winner_from_data("ice_hockey", "Men")
        elif cat.id == "prop_womens_figure_skating_country":
            leader = _get_event_winner_from_data("figure_skating", "Women's Singles")
        elif cat.id == "prop_most_individual_medals":
            leader = _get_most_individual_medals_leader()

        if leader:
            projected[cat.id] = [c.strip() for c in leader.split(",")]

    return projected


def update_results_from_scraper():
    """
    Fetch Olympics.com data and update category results in the DB.
    Only saves results for categories whose last_event_date has passed,
    preventing premature results from partial data.
    Cleans up any previously saved premature results.
    Skips categories that need admin entry.
    """
    existing_results = get_category_results()

    # Sport-level categories: country with most golds
    for sport_id in _DISCIPLINE_TO_SPORT_ID.values():
        if not _category_is_complete(sport_id):
            # Remove premature result if one was saved earlier
            if sport_id in existing_results:
                delete_category_result(sport_id)
            continue
        leader = _get_sport_gold_leader_from_data(sport_id)
        if leader:
            # Always update — results may change as late events finish
            existing = existing_results.get(sport_id)
            existing_str = ",".join(existing) if existing else None
            if existing_str != leader:
                if existing:
                    delete_category_result(sport_id)
                save_category_result(sport_id, leader)

    # Overall: country with most golds across all sports
    if not _category_is_complete("overall"):
        if "overall" in existing_results:
            delete_category_result("overall")
    else:
        overall_leader = _get_overall_gold_leader_from_data()
        if overall_leader:
            existing = existing_results.get("overall")
            existing_str = ",".join(existing) if existing else None
            if existing_str != overall_leader:
                if existing:
                    delete_category_result("overall")
                save_category_result("overall", overall_leader)

    # Featured: Men's Ice Hockey Gold
    hockey_cat_id = "featured_mens_ice_hockey_gold"
    if not _category_is_complete(hockey_cat_id):
        if hockey_cat_id in existing_results:
            delete_category_result(hockey_cat_id)
    else:
        winner = _get_event_winner_from_data("ice_hockey", "Men")
        if winner:
            existing = existing_results.get(hockey_cat_id)
            existing_str = ",".join(existing) if existing else None
            if existing_str != winner:
                if existing:
                    delete_category_result(hockey_cat_id)
                save_category_result(hockey_cat_id, winner)

    # Featured: Women's Figure Skating Singles country
    fs_cat_id = "prop_womens_figure_skating_country"
    if not _category_is_complete(fs_cat_id):
        if fs_cat_id in existing_results:
            delete_category_result(fs_cat_id)
    else:
        winner = _get_event_winner_from_data("figure_skating", "Women Single")
        if winner:
            existing = existing_results.get(fs_cat_id)
            existing_str = ",".join(existing) if existing else None
            if existing_str != winner:
                if existing:
                    delete_category_result(fs_cat_id)
                save_category_result(fs_cat_id, winner)

    # Prop: USA Figure Skating total medals
    usa_fs_cat_id = "prop_usa_figure_skating_medals"
    if not _category_is_complete(usa_fs_cat_id):
        if usa_fs_cat_id in existing_results:
            delete_category_result(usa_fs_cat_id)
    else:
        count = _get_usa_figure_skating_medal_count()
        if count:
            existing = existing_results.get(usa_fs_cat_id)
            existing_str = ",".join(existing) if existing else None
            if existing_str != count:
                if existing:
                    delete_category_result(usa_fs_cat_id)
                save_category_result(usa_fs_cat_id, count)
