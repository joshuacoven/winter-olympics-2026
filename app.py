"""
Winter Olympics 2026 Prediction Game

A Streamlit app for friends to predict gold medal winners and compete.
"""

import os
import time
import logging
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

from categories import get_all_categories, get_sports_list, get_countries, PredictionCategory, ANSWER_COUNTRY, ANSWER_YES_NO, ANSWER_NUMBER
from database import (
    create_pool, get_pool, get_pool_by_name, pool_exists, pool_name_exists,
    create_user, user_exists, verify_pin, get_user_pools, add_pool_member, is_pool_admin,
    create_prediction_set, get_user_prediction_sets, get_prediction_set,
    delete_prediction_set, assign_prediction_set_to_pool, get_pool_assignment,
    save_set_prediction, get_predictions_for_set, get_category_results,
    get_pool_assignments_for_pool, save_category_result
)
from scraper import update_results_from_scraper, ADMIN_ONLY_CATEGORIES

# Page config
st.set_page_config(
    page_title="Winter Olympics 2026 Predictions",
    page_icon="",
    layout="wide"
)

# Common timezones for the app
TIMEZONES = [
    "US/Eastern",
    "US/Central",
    "US/Mountain",
    "US/Pacific",
    "Europe/London",
    "Europe/Paris",
    "Europe/Rome",
    "Europe/Berlin",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Australia/Sydney",
]

# Initialize session state
if "pool_code" not in st.session_state:
    st.session_state.pool_code = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "timezone" not in st.session_state:
    st.session_state.timezone = "US/Eastern"
if "current_set_id" not in st.session_state:
    st.session_state.current_set_id = None

# Custom CSS with Design System
st.markdown("""
<style>
    /* ========================================
       DESIGN SYSTEM - CSS Variables
       ======================================== */
    :root {
        /* Spacing Scale (4px base) */
        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 16px;
        --space-lg: 24px;
        --space-xl: 32px;
        --space-2xl: 48px;

        /* Typography Scale */
        --text-xs: 12px;
        --text-sm: 14px;
        --text-base: 16px;
        --text-lg: 18px;
        --text-xl: 20px;
        --text-2xl: 24px;
        --text-3xl: 28px;

        /* Font Weights */
        --font-normal: 400;
        --font-medium: 500;
        --font-semibold: 600;
        --font-bold: 700;

        /* Line Heights */
        --leading-tight: 1.25;
        --leading-normal: 1.5;
        --leading-relaxed: 1.625;

        /* Interactive Element Sizing */
        --input-height: 44px;
        --input-height-sm: 38px;
        --button-height: 44px;
        --button-padding-x: var(--space-md);
        --touch-target-min: 44px;

        /* Border Radius */
        --radius-sm: 4px;
        --radius-md: 8px;
        --radius-lg: 12px;
        --radius-pill: 25px;

        /* Colors */
        --color-primary: #3d5a80;
        --color-text: #1a1a1a;
        --color-text-secondary: #666666;
        --color-text-muted: #999999;
        --color-border: #e0e0e0;
        --color-border-hover: #ccc;
        --color-bg: #ffffff;
        --color-bg-secondary: #f8f9fa;
    }

    /* ========================================
       GLOBAL TYPOGRAPHY
       ======================================== */
    .stApp {
        font-size: var(--text-base);
        line-height: var(--leading-normal);
    }

    /* Hide anchor links on headers */
    h1 a, h2 a, h3 a, h4 a {
        display: none !important;
    }

    /* Page Titles */
    h1 {
        font-size: var(--text-3xl) !important;
        font-weight: var(--font-bold) !important;
        line-height: var(--leading-tight) !important;
        margin-bottom: var(--space-lg) !important;
    }

    /* Section Headers */
    h2 {
        font-size: var(--text-2xl) !important;
        font-weight: var(--font-semibold) !important;
        line-height: var(--leading-tight) !important;
        margin-bottom: var(--space-md) !important;
    }

    h3 {
        font-size: var(--text-xl) !important;
        font-weight: var(--font-semibold) !important;
        line-height: var(--leading-tight) !important;
        margin-bottom: var(--space-md) !important;
    }

    /* ========================================
       SIDEBAR
       ======================================== */
    [data-testid="stSidebar"] {
        min-width: 220px;
        max-width: 280px;
    }

    /* Sidebar Navigation */
    .stRadio > div {
        flex-direction: column;
        gap: var(--space-xs);
    }
    .stRadio > div > label {
        padding: var(--space-sm) var(--space-md);
        border-radius: var(--radius-md);
        min-height: var(--touch-target-min);
        display: flex;
        align-items: center;
        transition: background-color 0.2s ease;
    }
    .stRadio > div > label:hover {
        background-color: rgba(151, 166, 195, 0.15);
    }
    .stRadio > div > label > div:first-child {
        display: none;
    }

    /* ========================================
       FORM ELEMENTS
       ======================================== */

    /* All Selectboxes - Base Styling */
    [data-testid="stSelectbox"] {
        cursor: pointer !important;
    }
    [data-testid="stSelectbox"] * {
        cursor: pointer !important;
    }
    [data-testid="stSelectbox"] > div > div {
        border-radius: var(--radius-md);
        border: 1px solid var(--color-border);
        font-size: var(--text-base);
        transition: border-color 0.2s ease;
    }
    [data-testid="stSelectbox"] > div > div:hover {
        border-color: var(--color-border-hover);
    }

    /* Filter Pills - Specific Styling */
    .filter-row [data-testid="stSelectbox"] {
        min-width: 140px;
        max-width: 200px;
    }
    .filter-row [data-testid="stSelectbox"] > div > div {
        border-radius: var(--radius-pill);
    }

    /* Text Inputs */
    [data-testid="stTextInput"] input {
        min-height: var(--input-height);
        padding: var(--space-sm) var(--space-md);
        font-size: var(--text-base);
        border-radius: var(--radius-md);
    }

    /* Hide "Press Enter to apply" helper text */
    .stTextInput div[data-testid="InputInstructions"] {
        display: none;
    }

    /* ========================================
       BUTTONS
       ======================================== */

    /* Primary Buttons */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button {
        min-height: var(--button-height);
        font-size: var(--text-base);
        font-weight: var(--font-medium);
        border-radius: var(--radius-md);
    }

    /* Secondary Buttons (text-style for Delete Set, etc.) */
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        color: var(--color-text-secondary) !important;
        font-size: var(--text-sm);
        font-weight: var(--font-medium);
    }
    .stButton > button[kind="secondary"]:hover {
        background: transparent !important;
        color: var(--color-text) !important;
    }

    /* ========================================
       TABS
       ======================================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: var(--space-sm);
        margin-bottom: var(--space-lg);
    }
    .stTabs [data-baseweb="tab"] {
        min-height: var(--touch-target-min);
        padding: var(--space-sm) var(--space-md);
        font-size: var(--text-base);
        font-weight: var(--font-medium);
        border-radius: var(--radius-md);
    }

    /* ========================================
       CARDS & CONTAINERS
       ======================================== */

    /* Streamlit containers with border */
    [data-testid="stVerticalBlock"] > div[data-testid="element-container"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: var(--space-md);
        border-radius: var(--radius-lg);
    }

    /* Card grid spacing */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        margin-bottom: var(--space-md);
        gap: var(--space-md);
    }

    /* Expanders */
    [data-testid="stExpander"] {
        border-radius: var(--radius-lg);
        margin-bottom: var(--space-md);
    }
    [data-testid="stExpander"] summary {
        padding: var(--space-md);
        font-size: var(--text-base);
        font-weight: var(--font-medium);
    }

    /* ========================================
       PROGRESS BAR
       ======================================== */
    .stProgress {
        margin-top: var(--space-lg);
        margin-bottom: var(--space-md);
    }
    .stProgress > div {
        height: 8px;
        border-radius: var(--radius-sm);
    }

    /* ========================================
       DATA DISPLAY
       ======================================== */

    /* Captions */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-size: var(--text-sm);
        color: var(--color-text-secondary);
        line-height: var(--leading-normal);
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        margin-top: var(--space-md);
    }

    /* ========================================
       SPACING UTILITIES
       ======================================== */

    /* Section spacing */
    hr {
        margin: var(--space-lg) 0;
    }

    /* Info/Warning/Error boxes */
    .stAlert {
        padding: var(--space-md) !important;
        padding-left: var(--space-md) !important;
        margin-left: 0 !important;
        border-radius: var(--radius-md) !important;
        margin-bottom: var(--space-md) !important;
        border-left: none !important;
    }
    [data-testid="stAlert"] {
        padding: var(--space-md) !important;
        padding-left: var(--space-md) !important;
        margin-left: 0 !important;
        border-radius: var(--radius-md) !important;
        margin-bottom: var(--space-md) !important;
        border-left: none !important;
    }
</style>
""", unsafe_allow_html=True)


def format_datetime(dt: datetime, tz_name: str) -> str:
    """Format datetime in the user's timezone."""
    rome_tz = ZoneInfo("Europe/Rome")
    user_tz = ZoneInfo(tz_name)
    dt_rome = dt.replace(tzinfo=rome_tz)
    dt_user = dt_rome.astimezone(user_tz)
    return dt_user.strftime("%b %d, %I:%M %p %Z")


def is_category_locked(category: PredictionCategory) -> bool:
    """Check if a category is locked (first event has started)."""
    if not category.first_event_date:
        return False
    rome_tz = ZoneInfo("Europe/Rome")
    simulate_date = os.environ.get("SIMULATE_DATE")
    if simulate_date:
        now = datetime.fromisoformat(simulate_date).replace(tzinfo=rome_tz)
    else:
        now = datetime.now(rome_tz)
    event_start = category.first_event_date.replace(tzinfo=rome_tz)
    return now >= event_start


def render_category_card(
    category: PredictionCategory,
    prediction: str | None,
    result: str | None,
    countries: list[str],
    tz_name: str,
    on_change_callback,
    card_key: str
):
    """Render a single category as a card."""
    locked = is_category_locked(category)

    # Determine status styling
    if result:
        if prediction and prediction == result:
            status_text = "Correct!"
            status_color = "#28a745"
        elif prediction:
            status_text = "Wrong"
            status_color = "#dc3545"
        else:
            status_text = "No prediction"
            status_color = "#6c757d"
    else:
        status_text = None
        status_color = None

    with st.container(border=True):
        # Category name
        st.markdown(f"**{category.display_name}**")

        # Tags
        gold_word = "Gold" if category.event_count == 1 else "Golds"

        if category.is_overall:
            tags_html = f'<span style="background-color: #ffc107; color: #000; padding: 2px 8px; border-radius: 10px; font-size: 0.75em;">{category.event_count} Gold Medals</span>'
        elif category.is_featured:
            tags_html = (
                f'<span style="background-color: #e74c3c; color: #fff; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em; margin-right: 6px;">Featured</span>'
                f'<span style="background-color: #2c3e50; color: #fff; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em;">{category.sport}</span>'
            )
        else:
            tags_html = (
                f'<span style="background-color: #ffc107; color: #000; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em;">{category.event_count} {gold_word}</span>'
            )

        # Add status tag
        if result:
            tags_html += ' <span style="background-color: #0085C7; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75em;">Completed</span>'
        elif locked:
            tags_html += ' <span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75em;">Locked</span>'

        st.markdown(tags_html, unsafe_allow_html=True)

        # Date range
        if category.first_event_date and category.last_event_date:
            st.caption(
                f"**Events:** {format_datetime(category.first_event_date, tz_name)} - "
                f"{format_datetime(category.last_event_date, tz_name)}"
            )

        # Prediction display/input
        if locked:
            if prediction:
                st.markdown(f"**Your pick:** {prediction}")
            else:
                st.markdown("*No prediction made*", help="Event has started")
        elif category.answer_type == ANSWER_YES_NO:
            options = ["", "Yes", "No"]
            current_idx = options.index(prediction) if prediction in options else 0
            selected = st.selectbox(
                "Prediction", options=options, index=current_idx,
                key=card_key, label_visibility="collapsed"
            )
            if selected and selected != prediction:
                on_change_callback(category.id, selected)
        elif category.answer_type == ANSWER_NUMBER:
            current_val = prediction or ""
            selected = st.text_input(
                "Prediction", value=current_val,
                placeholder="Enter a number",
                key=card_key, label_visibility="collapsed"
            )
            if selected and selected != prediction and selected.isdigit():
                on_change_callback(category.id, selected)
        else:
            # Country dropdown (default)
            countries_with_empty = [""] + countries
            current_idx = countries_with_empty.index(prediction) if prediction in countries_with_empty else 0
            selected = st.selectbox(
                "Prediction", options=countries_with_empty, index=current_idx,
                key=card_key, label_visibility="collapsed"
            )
            if selected and selected != prediction:
                on_change_callback(category.id, selected)

        # Show result if available
        if result and status_color:
            st.markdown(
                f'<span style="font-size: 0.85em; color: {status_color}; font-weight: 500;">'
                f'{result} - {status_text}</span>',
                unsafe_allow_html=True
            )


def login_page():
    """Login page."""
    st.title("Winter Olympics 2026 Prediction Game")
    st.write("Predict which countries win the most gold medals!")

    st.subheader("Log In or Create an Account")
    with st.form("login"):
        username = st.text_input("Username", placeholder="Enter your username")
        pin = st.text_input("3-digit PIN", placeholder="e.g., 123", max_chars=3)
        st.caption("The PIN is just to prevent accidental logins to someone else's account.")
        submitted = st.form_submit_button("Continue")

        if submitted:
            if not username:
                st.error("Please enter a username")
            elif not pin or not pin.isdigit() or len(pin) != 3:
                st.error("PIN must be 3 digits")
            elif len(username.strip()) < 2 or len(username.strip()) > 30:
                st.error("Username must be between 2 and 30 characters")
            else:
                username = username.strip()
                if not user_exists(username):
                    create_user(username, pin)
                    st.success(f"Welcome, {username}! Account created.")
                    st.session_state.user_name = username
                    st.rerun()
                else:
                    if verify_pin(username, pin):
                        st.success(f"Welcome back, {username}!")
                        st.session_state.user_name = username
                        st.rerun()
                    else:
                        st.error("Incorrect PIN")


def my_predictions_page():
    """Page for managing prediction sets."""
    st.title("My Predictions")

    # Get user's prediction sets
    sets = get_user_prediction_sets(st.session_state.user_name)

    # Handle case with no sets
    if not sets:
        st.info("Which country do you think will win the most gold medals in each category? Create a set of predictions that you can then assign to pools to compete against your friends!")
        col1, col2 = st.columns([3, 1])
        with col1:
            new_set_name = st.text_input(
                "Set name",
                placeholder="e.g., My Bold Picks",
                key="first_set_name_input",
                label_visibility="collapsed"
            )
        with col2:
            if st.button("Create", use_container_width=True, type="primary"):
                if new_set_name:
                    set_id = create_prediction_set(st.session_state.user_name, new_set_name.strip())
                    if set_id:
                        st.session_state.current_set_id = set_id
                        st.rerun()
                    else:
                        st.error("A set with that name already exists")
        return

    # Build tab names: prediction set names + "+" for new
    tab_names = [s["name"] for s in sets] + ["➕"]

    # Create tabs
    tabs = st.tabs(tab_names)

    # Render content for each prediction set tab
    for i, pred_set in enumerate(sets):
        with tabs[i]:
            st.session_state.current_set_id = pred_set["id"]
            render_prediction_set_content(pred_set)

    # Render the "+" tab content for creating new sets
    with tabs[-1]:
        st.subheader("Create New Prediction Set")
        col1, col2 = st.columns([3, 1])
        with col1:
            new_set_name = st.text_input(
                "Set name",
                placeholder="e.g., My Bold Picks",
                key="new_set_name_input",
                label_visibility="collapsed"
            )
        with col2:
            if st.button("Create", use_container_width=True, type="primary", key="create_new_set_btn"):
                if new_set_name:
                    set_id = create_prediction_set(st.session_state.user_name, new_set_name.strip())
                    if set_id:
                        st.success(f"Created '{new_set_name}'")
                        st.session_state.current_set_id = set_id
                        st.rerun()
                    else:
                        st.error("A set with that name already exists")
                else:
                    st.error("Please enter a name for the set")


def render_cards_grid(categories, predictions, results, countries, tz_name, save_callback, set_id):
    """Render a list of categories as a 3-column card grid."""
    num_cols = 3
    for i in range(0, len(categories), num_cols):
        cols = st.columns(num_cols, gap="small")
        for j, col in enumerate(cols):
            if i + j < len(categories):
                category = categories[i + j]
                prediction = predictions.get(category.id)
                result = results.get(category.id)
                with col:
                    render_category_card(
                        category=category,
                        prediction=prediction,
                        result=result,
                        countries=countries,
                        tz_name=tz_name,
                        on_change_callback=save_callback,
                        card_key=f"pred_{set_id}_{category.id}"
                    )


def render_prediction_set_content(pred_set):
    """Render the content for a prediction set tab."""
    set_id = pred_set["id"]

    # Get categories and predictions
    all_categories = get_all_categories()
    predictions = get_predictions_for_set(set_id)
    results = get_category_results()
    countries = get_countries()

    # Split into featured and sport-level
    featured_cats = [c for c in all_categories if c.is_featured]
    sport_cats = [c for c in all_categories if not c.is_featured]

    # Sort featured by date
    featured_cats = sorted(featured_cats, key=lambda c: (c.first_event_date or datetime.max))

    # Predictions count and Delete Set row
    col_count, col_delete = st.columns([3, 1])
    made_predictions = len(predictions)
    total_categories = len(all_categories)
    with col_count:
        st.write(f"**{made_predictions}** of **{total_categories}** predictions made")
    with col_delete:
        confirm_key = f"confirm_delete_{set_id}"
        if st.session_state.get(confirm_key):
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, delete", key=f"yes_delete_{set_id}", type="primary"):
                    delete_prediction_set(set_id)
                    st.session_state.current_set_id = None
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
            with col_no:
                if st.button("Cancel", key=f"cancel_delete_{set_id}", type="secondary"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
        else:
            if st.button("Delete Set", key=f"delete_set_{set_id}", type="secondary"):
                st.session_state[confirm_key] = True
                st.rerun()

    # Callback for saving predictions
    def save_prediction(category_id: str, country: str):
        save_set_prediction(set_id, category_id, country)
        st.rerun()

    # === FEATURED PREDICTIONS SECTION ===
    st.subheader("Featured Predictions")
    render_cards_grid(featured_cats, predictions, results, countries,
                      st.session_state.timezone, save_prediction, set_id)

    # === DIVIDER ===
    st.markdown("---")

    # === SORT for sport-level categories ===
    sort_col, _ = st.columns([1, 3])
    with sort_col:
        sort_by = st.selectbox(
            "Sort",
            options=["Sort: Event Date", "Sort: Alphabetical"],
            key=f"pred_sort_by_{set_id}",
            label_visibility="collapsed"
        )

    if sort_by == "Sort: Event Date":
        sport_cats = sorted(sport_cats, key=lambda c: c.first_event_date or datetime.max)
    else:
        sport_cats = sorted(sport_cats, key=lambda c: c.display_name)

    # === SPORT-LEVEL CARDS ===
    render_cards_grid(sport_cats, predictions, results, countries,
                      st.session_state.timezone, save_prediction, set_id)


def pools_page():
    """Page for managing pools and assignments."""
    st.title("My Pools")

    # Get user's pools and prediction sets
    pools = get_user_pools(st.session_state.user_name)
    prediction_sets = get_user_prediction_sets(st.session_state.user_name)

    # Join/Create pool buttons
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("Join a Pool", expanded=st.session_state.get("expand_join", False)):
            join_name = st.text_input("Pool Name", placeholder="Office Pool 2026", key="join_pool_name")
            if st.button("Join Pool"):
                if join_name:
                    pool = get_pool_by_name(join_name.strip())
                    if pool:
                        add_pool_member(pool['code'], st.session_state.user_name)
                        st.session_state.expand_join = False
                        st.success(f"Joined {pool['name']}!")
                        st.rerun()
                    else:
                        st.error("Pool not found")

    with col2:
        with st.expander("Create a Pool", expanded=st.session_state.get("expand_create", False)):
            pool_name = st.text_input("Pool Name", placeholder="Office Pool 2026", key="new_pool_name")
            if st.button("Create Pool"):
                if pool_name:
                    result = create_pool(pool_name.strip(), st.session_state.user_name)
                    if result:
                        st.session_state.expand_create = False
                        st.success(f"Pool '{result}' created!")
                        st.rerun()
                    else:
                        st.error("A pool with that name already exists")

    st.markdown("---")

    if not pools:
        return

    # List pools with assignment options
    st.subheader("Your Pools")

    for pool in pools:
        with st.container(border=True):
            if prediction_sets:
                col1, col2, col3 = st.columns([2, 2, 1])
            else:
                col1, col3 = st.columns([4, 1])

            with col1:
                st.markdown(f"**{pool['name']}**")

            if prediction_sets:
                with col2:
                    # Current assignment
                    current_assignment = get_pool_assignment(pool['code'], st.session_state.user_name)
                    set_options = {s["id"]: s["name"] for s in prediction_sets}
                    set_options[0] = "-- Select a prediction set --"
                    set_ids = [0] + list(s["id"] for s in prediction_sets)

                    current_idx = set_ids.index(current_assignment) if current_assignment in set_ids else 0

                    selected_set = st.selectbox(
                        "Prediction Set",
                        options=set_ids,
                        format_func=lambda x: set_options.get(x, "Unknown"),
                        index=current_idx,
                        key=f"pool_assign_{pool['code']}",
                        label_visibility="collapsed"
                    )

                    if selected_set != current_assignment and selected_set != 0:
                        assign_prediction_set_to_pool(pool['code'], st.session_state.user_name, selected_set)
                        st.rerun()

            with col3:
                if st.button("View", key=f"view_{pool['code']}", use_container_width=True):
                    st.session_state.pool_code = pool['code']
                    st.session_state.view_pool = True
                    st.rerun()

    if pools and not prediction_sets:
        st.caption("Create a prediction set in 'My Predictions' to assign to your pools.")


def get_pool_data(pool_code: str):
    """Get all data needed for pool views."""
    assignments = get_pool_assignments_for_pool(pool_code)
    categories = get_all_categories()
    results = get_category_results()

    if not assignments:
        return None

    users = sorted(assignments.keys())
    user_predictions = {user: get_predictions_for_set(set_id) for user, set_id in assignments.items()}

    # Calculate scores
    scores = {}
    for user in users:
        correct = sum(
            1 for cat in categories
            if cat.id in results and user_predictions[user].get(cat.id) == results[cat.id]
        )
        total = len(user_predictions[user])
        scores[user] = {"correct": correct, "total": total}

    sorted_users = sorted(users, key=lambda u: scores[u]["correct"], reverse=True)

    return {
        "users": users,
        "user_predictions": user_predictions,
        "scores": scores,
        "sorted_users": sorted_users,
        "categories": categories,
        "results": results,
        "assignments": assignments
    }


def pool_view_page(show_header: bool = True):
    """View a specific pool - top 3 leaderboard, user's picks, locked comparisons."""
    pool = get_pool(st.session_state.pool_code)
    if not pool:
        st.error("Pool not found")
        return

    if show_header:
        st.title(f"Pool: {pool['name']}")

        if st.button("Back to My Pools"):
            st.session_state.view_pool = False
            st.rerun()

        st.markdown("---")

    # Get pool data
    data = get_pool_data(pool['code'])

    if not data:
        st.info("No one has assigned predictions to this pool yet.")
        return

    current_user = st.session_state.user_name
    sorted_users = data["sorted_users"]
    scores = data["scores"]
    user_predictions = data["user_predictions"]
    categories = data["categories"]
    results = data["results"]

    # === TOP 3 LEADERBOARD ===
    st.subheader("Top 3")

    top3_html = '<div style="width: 100%;">'
    top3_html += '<div style="display: flex; padding: 8px 0; border-bottom: 1px solid #e0e0e0;">'
    top3_html += '<div style="flex: 1; font-weight: 600; color: #666;">Placement</div>'
    top3_html += '<div style="flex: 3; font-weight: 600; color: #666;">User</div>'
    top3_html += '<div style="flex: 2; font-weight: 600; color: #666; text-align: right;">Correct Picks</div>'
    top3_html += '</div>'

    for i, user in enumerate(sorted_users[:3]):
        rank = i + 1
        is_current = user == current_user
        name_display = f"<strong>{user}</strong> (you)" if is_current else user
        score_display = f"<strong>{scores[user]['correct']}</strong> / {scores[user]['total']}"
        border = 'border-bottom: 1px solid #f0f0f0;' if i < 2 else ''

        top3_html += f'<div style="display: flex; padding: 12px 0; {border} align-items: center;">'
        top3_html += f'<div style="flex: 1; font-weight: 700;">#{rank}</div>'
        top3_html += f'<div style="flex: 3;">{name_display}</div>'
        top3_html += f'<div style="flex: 2; text-align: right;">{score_display}</div>'
        top3_html += '</div>'

    top3_html += '</div>'
    st.markdown(top3_html, unsafe_allow_html=True)

    if st.button("See full standings →", type="secondary", key="go_to_leaderboard"):
        st.session_state.view_pool = False
        st.session_state.nav_override = "Leaderboard"
        st.session_state.pool_code = pool['code']
        st.rerun()

    # === YOUR PREDICTIONS ===
    st.markdown("---")
    st.subheader("Your Predictions")

    if current_user in user_predictions:
        import pandas as pd

        my_predictions = user_predictions[current_user]
        made = len(my_predictions)
        correct = scores[current_user]["correct"] if current_user in scores else 0

        st.write(f"**{made}** predictions made | **{correct}** correct so far")

        # Build table with all categories
        rows = []
        for cat in categories:
            pred = my_predictions.get(cat.id, "-")
            result = results.get(cat.id, "TBD")
            rows.append({
                "Category": cat.display_name,
                "Your Pick": pred,
                "Result": result,
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("You haven't assigned a prediction set to this pool yet.")

    # === LOCKED PREDICTIONS COMPARISON ===
    st.markdown("---")
    st.subheader("Predictions Comparison (Locked Events)")

    locked_categories = [c for c in categories if is_category_locked(c)]

    if not locked_categories:
        st.info("No events have started yet. Comparisons will appear here once events begin.")
        return

    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        sport_filter = st.selectbox(
            "Sport",
            options=["All"] + get_sports_list(),
            key="pool_sport_filter"
        )
    with col2:
        gender_filter = st.selectbox(
            "Gender",
            options=["All", "Men", "Women", "Mixed"],
            key="pool_gender_filter"
        )

    # Apply filters to locked categories only
    filtered = locked_categories
    if sport_filter != "All":
        filtered = [c for c in filtered if c.sport == sport_filter]
    if gender_filter != "All":
        filtered = [c for c in filtered if c.gender == gender_filter]

    if not filtered:
        st.info("No locked events match your filters.")
        return

    # Build comparison table
    import pandas as pd
    rows = []
    for cat in filtered:
        row = {"Category": cat.display_name}
        for user in data["users"]:
            row[user] = user_predictions[user].get(cat.id, "-")
        row["Result"] = results.get(cat.id, "TBD")
        rows.append(row)

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def results_page():
    """Show actual Olympic results with medal tally."""
    st.title("Results")

    categories = get_all_categories()
    results = get_category_results()

    # Get completed categories (have results)
    completed = [(c, results[c.id]) for c in categories if c.id in results]

    # Sort by last_event_date (completion date)
    completed.sort(key=lambda x: x[0].last_event_date or datetime.max)

    # === MEDAL TALLY ===
    st.subheader("Total Gold Medals")

    # Count golds by country
    gold_counts = {}
    for cat, winner in completed:
        gold_counts[winner] = gold_counts.get(winner, 0) + cat.event_count

    if gold_counts:
        # Sort by count descending
        sorted_countries = sorted(gold_counts.items(), key=lambda x: x[1], reverse=True)

        # Display as table
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("**Country**")
        with col2:
            st.markdown("**Gold Medals**")

        for i, (country, count) in enumerate(sorted_countries):
            medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, "")
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"{medal} {country}")
            with col2:
                st.write(f"**{count}**")
    else:
        st.info("Check back when events have been completed!")

    st.markdown("---")

    # === EVENT RESULTS ===
    st.subheader("Event Results")

    if not completed:
        st.info("Check back when events have been completed!")
        return

    st.caption(f"Showing {len(completed)} completed categories")

    for cat, winner in completed:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{cat.display_name}**")
            st.caption(f"{cat.sport} • {cat.event_count} {'Gold' if cat.event_count == 1 else 'Golds'}")
        with col2:
            st.write(f"🏆 {winner}")


def leaderboard_page():
    """Full leaderboard for a selected pool."""
    st.title("Leaderboard")

    pools = get_user_pools(st.session_state.user_name)

    if not pools:
        st.info("Join a pool to see leaderboards!")
        return

    # Select pool - constrained width
    pool_options = {p["code"]: p["name"] for p in pools}
    pool_col, _ = st.columns([1, 2])
    with pool_col:
        selected_pool = st.selectbox(
            "Select Pool",
            options=list(pool_options.keys()),
            format_func=lambda x: pool_options[x]
        )

    st.session_state.pool_code = selected_pool

    # Get pool data
    data = get_pool_data(selected_pool)

    if not data:
        st.info("No one has assigned predictions to this pool yet.")
        return

    current_user = st.session_state.user_name
    sorted_users = data["sorted_users"]
    scores = data["scores"]

    # Spacing between dropdown and table
    st.markdown("")

    # Full leaderboard - column headers + rows rendered as single HTML block
    leaderboard_html = '<div style="width: 100%;">'
    leaderboard_html += '<div style="display: flex; padding: 8px 0; border-bottom: 1px solid #e0e0e0;">'
    leaderboard_html += '<div style="flex: 1; font-weight: 600; color: #666;">Placement</div>'
    leaderboard_html += '<div style="flex: 3; font-weight: 600; color: #666;">User</div>'
    leaderboard_html += '<div style="flex: 2; font-weight: 600; color: #666; text-align: right;">Correct Picks</div>'
    leaderboard_html += '</div>'

    for i, user in enumerate(sorted_users):
        rank = i + 1
        is_current = user == current_user
        name_display = f"<strong>{user}</strong> (you)" if is_current else user
        score_display = f"<strong>{scores[user]['correct']}</strong> / {scores[user]['total']}"
        border = 'border-bottom: 1px solid #f0f0f0;' if i < len(sorted_users) - 1 else ''

        leaderboard_html += f'<div style="display: flex; padding: 12px 0; {border} align-items: center;">'
        leaderboard_html += f'<div style="flex: 1; font-weight: 700;">#{rank}</div>'
        leaderboard_html += f'<div style="flex: 3;">{name_display}</div>'
        leaderboard_html += f'<div style="flex: 2; text-align: right;">{score_display}</div>'
        leaderboard_html += '</div>'

    leaderboard_html += '</div>'
    st.markdown(leaderboard_html, unsafe_allow_html=True)



def admin_page():
    """Password-protected admin page for manually entering results."""
    st.title("Admin - Enter Results")

    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "olympics2026")

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        password = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        return

    # Show all categories with current results and input fields
    categories = get_all_categories()
    results = get_category_results()
    countries = get_countries()

    # Sort by first_event_date
    categories.sort(key=lambda c: c.first_event_date or datetime.max)

    st.write(f"**{len(results)}** of **{len(categories)}** results entered")
    st.markdown("---")

    for cat in categories:
        current_result = results.get(cat.id, None)
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.markdown(f"**{cat.display_name}**")
            st.caption(f"ID: `{cat.id}` | Type: {cat.answer_type}")

        with col2:
            if cat.answer_type == ANSWER_YES_NO:
                options = ["", "Yes", "No"]
                current_idx = options.index(current_result) if current_result in options else 0
                new_val = st.selectbox(
                    "Result", options=options, index=current_idx,
                    key=f"admin_{cat.id}", label_visibility="collapsed"
                )
            elif cat.answer_type == ANSWER_NUMBER:
                new_val = st.text_input(
                    "Result", value=current_result or "",
                    placeholder="Enter a number",
                    key=f"admin_{cat.id}", label_visibility="collapsed"
                )
            else:
                countries_with_empty = [""] + countries
                current_idx = countries_with_empty.index(current_result) if current_result in countries_with_empty else 0
                new_val = st.selectbox(
                    "Result", options=countries_with_empty, index=current_idx,
                    key=f"admin_{cat.id}", label_visibility="collapsed"
                )

        with col3:
            if st.button("Save", key=f"admin_save_{cat.id}"):
                if new_val:
                    save_category_result(cat.id, new_val)
                    st.rerun()

        if current_result:
            st.caption(f"Current result: **{current_result}**")


def main():
    """Main app logic."""
    # Check if user is logged in
    if not st.session_state.user_name:
        login_page()
        return

    # Run scraper at most once every 30 minutes (across all page loads)
    if "last_scrape_time" not in st.session_state:
        st.session_state.last_scrape_time = 0
    if time.time() - st.session_state.last_scrape_time > 1800:
        try:
            update_results_from_scraper()
            st.session_state.last_scrape_time = time.time()
        except Exception:
            logger.exception("Scraper failed")

    # Sidebar
    st.sidebar.markdown(f"**{st.session_state.user_name}**")

    # Timezone selector
    tz_idx = TIMEZONES.index(st.session_state.timezone) if st.session_state.timezone in TIMEZONES else 0
    selected_tz = st.sidebar.selectbox(
        "Timezone",
        options=TIMEZONES,
        index=tz_idx,
        key="nav_tz_select"
    )
    if selected_tz != st.session_state.timezone:
        st.session_state.timezone = selected_tz
        st.rerun()

    st.sidebar.markdown("---")

    # Navigation - add Admin if ?admin=1 in URL
    nav_options = ["My Predictions", "Pools", "Leaderboard", "Results"]
    query_params = st.query_params
    if query_params.get("admin") == "1":
        nav_options.append("Admin")

    nav_override = st.session_state.pop("nav_override", None)
    default_idx = nav_options.index(nav_override) if nav_override in nav_options else 0

    page = st.sidebar.radio(
        "Navigation",
        nav_options,
        index=default_idx,
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")

    if st.sidebar.button("Log Out"):
        st.session_state.user_name = None
        st.session_state.pool_code = None
        st.session_state.current_set_id = None
        st.rerun()

    # Render selected page
    if page == "My Predictions":
        my_predictions_page()
    elif page == "Pools":
        if st.session_state.get("view_pool"):
            pool_view_page()
        else:
            pools_page()
    elif page == "Leaderboard":
        leaderboard_page()
    elif page == "Results":
        results_page()
    elif page == "Admin":
        admin_page()


if __name__ == "__main__":
    main()
