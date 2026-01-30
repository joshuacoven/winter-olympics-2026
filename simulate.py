#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulate mid-Olympics state for UX testing.

Usage:
    python simulate.py          # Seed fake results, users, predictions, pool
    python simulate.py --clean  # Remove all simulated data

Then run the app with optional date override:
    SIMULATE_DATE=2026-02-10T12:00 streamlit run app.py
"""

import sys
import random
import string
from database import (
    get_connection, init_db, fetchone_dict, fetchall_dicts, _sync_if_turso,
    get_pool_by_name
)
from categories import get_all_categories, ANSWER_YES_NO, ANSWER_NUMBER
from events import WINTER_OLYMPICS_COUNTRIES

# Simulated date: Feb 15, 2026 (midway through the Games)
# Only include results for categories whose last_event_date <= Feb 15:
#   luge         ends Feb 13
#   skeleton     ends Feb 14
#   ski_jumping  ends Feb 14
SIMULATED_RESULTS = {
    "luge": "Germany",
    "skeleton": "Germany",
    "ski_jumping": "Norway",
}

# Test users: (username, pin)
TEST_USERS = [
    ("Alice", "111"),
    ("Bob", "222"),
    ("Carol", "333"),
    ("Dave", "444"),
]

TEST_POOL_NAME = "Test Pool"

# Countries to pick from for predictions
PRED_COUNTRIES = [
    "Norway", "Germany", "United States", "Canada", "Austria",
    "Switzerland", "Sweden", "Netherlands", "South Korea", "France",
    "Italy", "Finland", "Japan",
]


def seed():
    """Seed the database with simulated data. Uses batch SQL to minimize Turso syncs."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Insert results
    for cat_id, result in SIMULATED_RESULTS.items():
        cursor.execute("""
            INSERT INTO category_results (category_id, winning_country) VALUES (?, ?)
            ON CONFLICT(category_id) DO UPDATE SET winning_country = excluded.winning_country
        """, (cat_id, result))
    print(f"Inserted {len(SIMULATED_RESULTS)} category results.")

    # 2. Create test users with prediction sets
    all_categories = get_all_categories()
    set_ids = {}

    for username, pin in TEST_USERS:
        cursor.execute("INSERT OR IGNORE INTO users (username, pin) VALUES (?, ?)", (username, pin))
        cursor.execute(
            "INSERT OR IGNORE INTO prediction_sets (username, name) VALUES (?, ?)",
            (username, f"{username}'s Picks")
        )
        cursor.execute(
            "SELECT id FROM prediction_sets WHERE username = ? AND name = ?",
            (username, f"{username}'s Picks")
        )
        row = fetchone_dict(cursor)
        set_id = row["id"] if row else None

        if set_id:
            set_ids[username] = set_id
            for cat in all_categories:
                if cat.answer_type == ANSWER_YES_NO:
                    pred = random.choice(["Yes", "No"])
                elif cat.answer_type == ANSWER_NUMBER:
                    pred = str(random.randint(0, 6))
                else:
                    pred = random.choice(PRED_COUNTRIES)
                cursor.execute("""
                    INSERT INTO predictions_v2 (prediction_set_id, category_id, country) VALUES (?, ?, ?)
                    ON CONFLICT(prediction_set_id, category_id) DO UPDATE SET country = excluded.country
                """, (set_id, cat.id, pred))

    print(f"Created {len(TEST_USERS)} test users with predictions.")

    # 3. Bias predictions so scores differ
    accuracy = {"Alice": 0.8, "Bob": 0.5, "Carol": 0.3, "Dave": 0.1}
    for username, target_acc in accuracy.items():
        set_id = set_ids.get(username)
        if not set_id:
            continue
        for cat_id, result in SIMULATED_RESULTS.items():
            if random.random() < target_acc:
                cursor.execute("""
                    INSERT INTO predictions_v2 (prediction_set_id, category_id, country) VALUES (?, ?, ?)
                    ON CONFLICT(prediction_set_id, category_id) DO UPDATE SET country = excluded.country
                """, (set_id, cat_id, result))

    print("Biased predictions for varied leaderboard scores.")

    # 4. Create pool and assign everyone
    conn.commit()
    _sync_if_turso(conn)

    pool = get_pool_by_name(TEST_POOL_NAME)
    if not pool:
        pool_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        cursor.execute("INSERT INTO pools (code, name, created_by) VALUES (?, ?, ?)",
                        (pool_code, TEST_POOL_NAME, "Alice"))
        cursor.execute("INSERT INTO pool_members (pool_code, username, is_admin) VALUES (?, ?, 1)",
                        (pool_code, "Alice"))
        conn.commit()
        _sync_if_turso(conn)
        pool = get_pool_by_name(TEST_POOL_NAME)

    for username, _ in TEST_USERS:
        cursor.execute(
            "INSERT OR IGNORE INTO pool_members (pool_code, username, is_admin) VALUES (?, ?, 0)",
            (pool["code"], username))
        set_id = set_ids.get(username)
        if set_id:
            cursor.execute("""
                INSERT INTO pool_prediction_set_assignments (pool_code, username, prediction_set_id)
                VALUES (?, ?, ?)
                ON CONFLICT(pool_code, username) DO UPDATE SET prediction_set_id = excluded.prediction_set_id
            """, (pool["code"], username, set_id))

    conn.commit()
    _sync_if_turso(conn)

    print(f"Created pool '{TEST_POOL_NAME}' with all test users assigned.")
    print("\nDone! Log in as Alice (PIN: 111), Bob (222), Carol (333), or Dave (444)")


def clean():
    """Remove all simulated data."""
    from database import fetchone_dict, fetchall_dicts, _sync_if_turso
    conn = get_connection()
    cursor = conn.cursor()

    # Remove only simulated category results (not real scraped ones)
    for cat_id in SIMULATED_RESULTS:
        cursor.execute("DELETE FROM category_results WHERE category_id = ?", (cat_id,))

    # Remove test users and their data
    for username, _ in TEST_USERS:
        # Get prediction set IDs
        cursor.execute("SELECT id FROM prediction_sets WHERE username = ?", (username,))
        set_rows = fetchall_dicts(cursor)
        for row in set_rows:
            cursor.execute("DELETE FROM predictions_v2 WHERE prediction_set_id = ?", (row["id"],))
            cursor.execute("DELETE FROM pool_prediction_set_assignments WHERE prediction_set_id = ?", (row["id"],))
        cursor.execute("DELETE FROM prediction_sets WHERE username = ?", (username,))
        cursor.execute("DELETE FROM pool_members WHERE username = ?", (username,))
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))

    # Remove test pool
    cursor.execute("SELECT code FROM pools WHERE name = ?", (TEST_POOL_NAME,))
    pool_row = fetchone_dict(cursor)
    if pool_row:
        cursor.execute("DELETE FROM pool_prediction_set_assignments WHERE pool_code = ?", (pool_row["code"],))
        cursor.execute("DELETE FROM pool_members WHERE pool_code = ?", (pool_row["code"],))
        cursor.execute("DELETE FROM pools WHERE code = ?", (pool_row["code"],))

    conn.commit()
    _sync_if_turso(conn)
    print("Cleaned up all simulated data.")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        clean()
    else:
        seed()
