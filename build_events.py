#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Joshua Coven

Goal:
    * Fetch official event names and dates from Olympics.com schedule page
    * Generate events.py with accurate, official data

Methodology:
    * Fetch https://www.olympics.com/en/milano-cortina-2026/schedule using curl
    * Extract `result_schedule_data` JSON embedded in a <script> tag
    * Process all schedule units across all day chunks
    * For each unique eventId with FNL (final) phases:
        - Get eventName, disciplineName, genderCode
        - Compute first_round_date = earliest startDate across all units
        - Compute gold_medal_date = latest startDate among FNL-/8FNL phase units
    * Write the output to events.py preserving all helper functions
"""

import re
import json
import subprocess
import sys
from datetime import datetime

SCHEDULE_URL = "https://www.olympics.com/en/milano-cortina-2026/schedule"

# Map Olympics.com discipline names to our sport names
DISCIPLINE_MAP = {
    "Bobsleigh": "Bobsled",
    # All others pass through as-is
}

# Map Olympics.com gender codes to display strings
GENDER_MAP = {
    "M": "Men",
    "W": "Women",
    "X": "Mixed",
}

# Browser headers required by Olympics.com (blocks requests without these)
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


def curl_fetch(url: str, timeout: int = 30) -> str | None:
    """Fetch a URL using curl subprocess (bypasses Olympics.com bot protection)."""
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
        print(f"ERROR: curl failed for {url}: returncode={result.returncode}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: curl subprocess failed for {url}: {e}", file=sys.stderr)
    return None


def extract_schedule_data(html: str) -> dict | None:
    """Extract result_schedule_data JSON from the HTML page."""
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for script in scripts:
        script = script.strip()
        if 'result_schedule_data' not in script or not script.startswith('{'):
            continue
        try:
            data = json.loads(script)
            return data.get('result_schedule_data')
        except (json.JSONDecodeError, KeyError):
            continue
    return None


def parse_events(schedule_data: dict) -> list[dict]:
    """Parse schedule data into a list of event dicts."""
    # Collect all units across all day chunks
    all_units = []
    for key, value in schedule_data.items():
        if key.startswith('initialSchedule_') and isinstance(value, dict):
            all_units.extend(value.get('units', []))

    # Group by eventId
    events = {}
    for unit in all_units:
        eid = unit['eventId']
        if eid not in events:
            events[eid] = {
                'eventName': unit['eventName'],
                'disciplineName': unit['disciplineName'],
                'genderCode': unit['genderCode'],
                'phases': set(),
                'all_starts': [],
                'final_starts': [],
            }
        events[eid]['phases'].add(unit['phaseCode'])
        events[eid]['all_starts'].append(unit['startDate'])
        # FNL- = final, 8FNL = eighth-final (but also counts as medal round for some)
        if unit['phaseCode'] in ('FNL-', '8FNL'):
            events[eid]['final_starts'].append(unit['startDate'])

    # Filter to medal events only (those with FNL- or 8FNL phases)
    medal_events = []
    for eid, ev in events.items():
        if not any(p in ('FNL-', '8FNL') for p in ev['phases']):
            continue

        sport = DISCIPLINE_MAP.get(ev['disciplineName'], ev['disciplineName'])
        gender = GENDER_MAP.get(ev['genderCode'], ev['genderCode'])
        name = ev['eventName']

        # Parse dates
        first_round = min(ev['all_starts'])
        gold_medal = max(ev['final_starts'])

        # Parse ISO datetime strings (e.g., "2026-02-07T11:30:00+01:00")
        # Strip timezone info for naive datetime (Rome/CET)
        first_dt = datetime.fromisoformat(first_round.replace('+01:00', '').replace('+02:00', ''))
        gold_dt = datetime.fromisoformat(gold_medal.replace('+01:00', '').replace('+02:00', ''))

        medal_events.append({
            'sport': sport,
            'name': name,
            'gender': gender,
            'first_round_date': first_dt,
            'gold_medal_date': gold_dt,
        })

    # Sort by sport, then gender, then first_round_date
    medal_events.sort(key=lambda e: (e['sport'], e['gender'], e['first_round_date']))
    return medal_events


def generate_events_py(events: list[dict]) -> str:
    """Generate the contents of events.py."""
    lines = []

    # Module docstring
    lines.append('"""')
    lines.append('Winter Olympics 2026 Milano-Cortina Events Data')
    lines.append('')
    lines.append(f'Auto-generated by build_events.py from Olympics.com schedule data.')
    lines.append(f'Contains all {len(events)} medal events with dates and metadata.')
    lines.append('Olympics run February 6-22, 2026.')
    lines.append('Times are in Europe/Rome timezone (CET/UTC+1).')
    lines.append('"""')
    lines.append('')
    lines.append('from datetime import datetime')
    lines.append('from dataclasses import dataclass')
    lines.append('from typing import Literal')
    lines.append('')

    # Countries list
    lines.append('# All countries competing in the 2026 Winter Olympics (93 NOCs + ROC/Russia)')
    lines.append('WINTER_OLYMPICS_COUNTRIES = [')
    countries = [
        '"Albania"', '"Andorra"', '"Argentina"', '"Armenia"', '"Australia"', '"Austria"',
        '"Azerbaijan"', '"Belgium"', '"Benin"', '"Bolivia"', '"Bosnia and Herzegovina"',
        '"Brazil"', '"Bulgaria"', '"Canada"', '"Chile"', '"China"', '"Chinese Taipei"',
        '"Colombia"', '"Croatia"', '"Cyprus"', '"Czech Republic"', '"Denmark"', '"Ecuador"',
        '"Eritrea"', '"Estonia"', '"Finland"', '"France"', '"Georgia"', '"Germany"',
        '"Great Britain"', '"Greece"', '"Guinea-Bissau"', '"Haiti"', '"Hong Kong"',
        '"Hungary"', '"Iceland"', '"India"', '"Individual Neutral Athletes"', '"Iran"',
        '"Ireland"', '"Israel"', '"Italy"', '"Jamaica"', '"Japan"', '"Kazakhstan"', '"Kenya"',
        '"Kosovo"', '"Kyrgyzstan"', '"Latvia"', '"Lebanon"', '"Liechtenstein"', '"Lithuania"',
        '"Luxembourg"', '"Madagascar"', '"Malaysia"', '"Malta"', '"Mexico"', '"Moldova"',
        '"Monaco"', '"Mongolia"', '"Montenegro"', '"Morocco"', '"Netherlands"',
        '"New Zealand"', '"Nigeria"', '"North Macedonia"', '"Norway"', '"Pakistan"',
        '"Philippines"', '"Poland"', '"Portugal"', '"Puerto Rico"', '"ROC/Russia"',
        '"Romania"', '"San Marino"', '"Saudi Arabia"', '"Serbia"', '"Singapore"',
        '"Slovakia"', '"Slovenia"', '"South Africa"', '"South Korea"', '"Spain"', '"Sweden"',
        '"Switzerland"', '"Thailand"', '"Trinidad and Tobago"', '"Turkey"', '"Ukraine"',
        '"United Arab Emirates"', '"United States"', '"Uruguay"', '"Uzbekistan"',
        '"Venezuela"',
    ]
    # Write 6 per line
    for i in range(0, len(countries), 6):
        chunk = countries[i:i+6]
        lines.append(f'    {", ".join(chunk)},')
    lines.append(']')
    lines.append('')

    # Gender type
    lines.append('# Gender type')
    lines.append('Gender = Literal["Men", "Women", "Mixed"]')
    lines.append('')
    lines.append('')

    # Event dataclass
    lines.append('@dataclass')
    lines.append('class Event:')
    lines.append('    """Represents a single Olympic event."""')
    lines.append('    sport: str')
    lines.append('    name: str')
    lines.append('    gender: Gender')
    lines.append('    first_round_date: datetime  # When the event starts (qualifying, first round, etc.)')
    lines.append('    gold_medal_date: datetime   # When the gold medal is awarded')
    lines.append('')
    lines.append('    @property')
    lines.append('    def event_id(self) -> str:')
    lines.append('        """Unique identifier for the event."""')
    lines.append('        return f"{self.sport} - {self.name}"')
    lines.append('')
    lines.append('    @property')
    lines.append('    def display_name(self) -> str:')
    lines.append('        """Display name with gender."""')
    lines.append('        return f"{self.name}"')
    lines.append('')
    lines.append('')

    # EVENTS_DATA
    lines.append(f'# All {len(events)} events with schedule (auto-generated from Olympics.com)')
    lines.append('EVENTS_DATA = [')

    current_sport = None
    for ev in events:
        if ev['sport'] != current_sport:
            if current_sport is not None:
                lines.append('')
            current_sport = ev['sport']
            sport_events = [e for e in events if e['sport'] == current_sport]
            lines.append(f'    # {current_sport} ({len(sport_events)} events)')

        first = ev['first_round_date']
        gold = ev['gold_medal_date']
        name_repr = repr(ev['name'])
        lines.append(
            f'    Event("{ev["sport"]}", {name_repr}, "{ev["gender"]}",\n'
            f'          datetime({first.year}, {first.month}, {first.day}, {first.hour}, {first.minute}), '
            f'datetime({gold.year}, {gold.month}, {gold.day}, {gold.hour}, {gold.minute})),'
        )

    lines.append(']')
    lines.append('')
    lines.append('')

    # Helper functions
    lines.append('def get_all_events() -> list[Event]:')
    lines.append('    """Return all events."""')
    lines.append('    return EVENTS_DATA')
    lines.append('')
    lines.append('')
    lines.append('def get_events_by_sport() -> dict[str, list[Event]]:')
    lines.append('    """Return events grouped by sport."""')
    lines.append('    sports = {}')
    lines.append('    for event in EVENTS_DATA:')
    lines.append('        if event.sport not in sports:')
    lines.append('            sports[event.sport] = []')
    lines.append('        sports[event.sport].append(event)')
    lines.append('    return sports')
    lines.append('')
    lines.append('')
    lines.append('def get_sports() -> list[str]:')
    lines.append('    """Return list of all sports."""')
    lines.append('    return sorted(set(e.sport for e in EVENTS_DATA))')
    lines.append('')
    lines.append('')
    lines.append('def get_countries() -> list[str]:')
    lines.append('    """Return list of countries for prediction dropdowns."""')
    lines.append('    return WINTER_OLYMPICS_COUNTRIES')
    lines.append('')
    lines.append('')
    lines.append('def filter_events(')
    lines.append('    events: list[Event],')
    lines.append('    sport: str | None = None,')
    lines.append('    gender: Gender | None = None')
    lines.append(') -> list[Event]:')
    lines.append('    """Filter events by sport and/or gender."""')
    lines.append('    result = events')
    lines.append('    if sport:')
    lines.append('        result = [e for e in result if e.sport == sport]')
    lines.append('    if gender:')
    lines.append('        result = [e for e in result if e.gender == gender]')
    lines.append('    return result')
    lines.append('')
    lines.append('')
    lines.append('def sort_events_by_date(events: list[Event], by_gold_medal: bool = False) -> list[Event]:')
    lines.append('    """Sort events by date (first round or gold medal)."""')
    lines.append('    if by_gold_medal:')
    lines.append('        return sorted(events, key=lambda e: e.gold_medal_date)')
    lines.append('    return sorted(events, key=lambda e: e.first_round_date)')
    lines.append('')

    return '\n'.join(lines) + '\n'


def main():
    print("Fetching Olympics.com schedule page...")
    html = curl_fetch(SCHEDULE_URL)
    if not html:
        print("ERROR: Failed to fetch schedule page", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(html):,} bytes")

    print("Extracting schedule data...")
    schedule_data = extract_schedule_data(html)
    if not schedule_data:
        print("ERROR: Could not find result_schedule_data in HTML", file=sys.stderr)
        sys.exit(1)

    # Count day chunks
    day_keys = [k for k in schedule_data if k.startswith('initialSchedule_')]
    print(f"Found {len(day_keys)} day chunks")

    print("Parsing events...")
    events = parse_events(schedule_data)
    print(f"Found {len(events)} medal events")

    # Summary by sport
    sports = {}
    for ev in events:
        sports.setdefault(ev['sport'], []).append(ev)
    print("\nEvents per sport:")
    for sport in sorted(sports):
        print(f"  {sport}: {len(sports[sport])}")

    # Gender breakdown
    men = sum(1 for e in events if e['gender'] == 'Men')
    women = sum(1 for e in events if e['gender'] == 'Women')
    mixed = sum(1 for e in events if e['gender'] == 'Mixed')
    print(f"\nGender breakdown: Men={men}, Women={women}, Mixed={mixed}")

    print("\nGenerating events.py...")
    output = generate_events_py(events)

    from pathlib import Path
    output_path = Path(__file__).parent / "events.py"
    output_path.write_text(output)
    print(f"Wrote {len(output):,} bytes to {output_path}")
    print(f"\nDone! {len(events)} events written to events.py")


if __name__ == "__main__":
    main()
