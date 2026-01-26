"""
Winter Olympics 2026 Prediction Game

A Streamlit app for friends to predict gold medal winners and compete.
"""

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

from categories import get_all_categories, get_sports_list, get_countries, PredictionCategory
from database import (
    create_pool, get_pool, get_pool_by_name, pool_exists, pool_name_exists,
    create_user, user_exists, get_user_pools, add_pool_member, is_pool_admin,
    create_prediction_set, get_user_prediction_sets, get_prediction_set,
    delete_prediction_set, assign_prediction_set_to_pool, get_pool_assignment,
    save_set_prediction, get_predictions_for_set, get_category_results,
    get_pool_assignments_for_pool
)

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
    [data-testid="stAlert"] {
        padding: var(--space-md);
        border-radius: var(--radius-md);
        margin-bottom: var(--space-md);
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

    # Gender tag colors
    gender_colors = {"Men": "#0d6efd", "Women": "#d63384", "Mixed": "#6f42c1", None: "#ffc107"}
    gender_color = gender_colors.get(category.gender, "#6c757d")

    with st.container(border=True):
        # Category name
        st.markdown(f"**{category.display_name}**")

        # Tags
        # Gold text formatting
        gold_word = "Gold" if category.event_count == 1 else "Golds"

        if category.is_overall:
            tags_html = f'<span style="background-color: #ffc107; color: #000; padding: 2px 8px; border-radius: 10px; font-size: 0.75em;">{category.event_count} Gold Medals</span>'
        else:
            tags_html = (
                f'<span style="background-color: #2c3e50; color: #fff; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em; margin-right: 6px;">{category.sport}</span>'
                f'<span style="background-color: {gender_color}; color: white; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em; margin-right: 6px;">{category.gender}</span>'
                f'<span style="background-color: #ffc107; color: #000; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em;">{category.event_count} {gold_word}</span>'
            )

        # Add locked tag if locked
        if locked and not result:
            tags_html += ' <span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75em;">Locked</span>'

        st.markdown(tags_html, unsafe_allow_html=True)

        # Date range
        if category.first_event_date and category.last_event_date:
            st.caption(
                f"**Events:** {format_datetime(category.first_event_date, tz_name)} - "
                f"{format_datetime(category.last_event_date, tz_name)}"
            )

        # Prediction display/dropdown
        if locked:
            # Show locked prediction (can't change)
            if prediction:
                st.markdown(f"**Your pick:** {prediction}")
            else:
                st.markdown("*No prediction made*", help="Event has started")
        else:
            # Editable dropdown
            countries_with_empty = [""] + countries
            current_idx = countries_with_empty.index(prediction) if prediction in countries_with_empty else 0

            selected = st.selectbox(
                "Prediction",
                options=countries_with_empty,
                index=current_idx,
                key=card_key,
                label_visibility="collapsed"
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
        submitted = st.form_submit_button("Continue")

        if submitted:
            if username:
                username = username.strip()
                if not user_exists(username):
                    create_user(username)
                    st.success(f"Welcome, {username}! Account created.")
                else:
                    st.success(f"Welcome back, {username}!")
                st.session_state.user_name = username
                st.rerun()
            else:
                st.error("Please enter a username")


def my_predictions_page():
    """Page for managing prediction sets."""
    st.title("My Predictions")
    st.caption("Predict which country will win the most gold medals in each category")

    # Get user's prediction sets
    sets = get_user_prediction_sets(st.session_state.user_name)

    # Handle case with no sets
    if not sets:
        st.info("Create a prediction set to start making predictions!")
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


def render_prediction_set_content(pred_set):
    """Render the content for a prediction set tab."""
    set_id = pred_set["id"]

    # Filters and delete on one row
    st.markdown('<div class="filter-row">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        sport_options = ["Sport (All)"] + get_sports_list()
        sport_filter = st.selectbox(
            "Sport",
            options=sport_options,
            key=f"pred_sport_filter_{set_id}",
            label_visibility="collapsed"
        )
        if sport_filter == "Sport (All)":
            sport_filter = "All"
    with col2:
        gender_options = ["Gender (All)", "Men", "Women", "Mixed"]
        gender_filter = st.selectbox(
            "Gender",
            options=gender_options,
            key=f"pred_gender_filter_{set_id}",
            label_visibility="collapsed"
        )
        if gender_filter == "Gender (All)":
            gender_filter = "All"
    with col3:
        sort_by = st.selectbox(
            "Sort",
            options=["Sort: Event Date", "Sort: Alphabetical"],
            key=f"pred_sort_by_{set_id}",
            label_visibility="collapsed"
        )
    with col4:
        if st.button("Delete Set", key=f"delete_set_{set_id}", type="secondary"):
            delete_prediction_set(set_id)
            st.session_state.current_set_id = None
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Get categories and predictions
    categories = get_all_categories()
    predictions = get_predictions_for_set(set_id)
    results = get_category_results()
    countries = get_countries()

    # Apply filters
    if sport_filter != "All":
        categories = [c for c in categories if c.sport == sport_filter]
    if gender_filter != "All":
        categories = [c for c in categories if c.gender == gender_filter]

    # Apply sorting
    if sort_by == "Sort: Event Date":
        # Sort by date, but keep overall categories first
        overall = [c for c in categories if c.is_overall]
        non_overall = [c for c in categories if not c.is_overall]
        non_overall = sorted(non_overall, key=lambda c: c.first_event_date or datetime.max)
        categories = overall + non_overall
    else:  # Alphabetical
        categories = sorted(categories, key=lambda c: c.display_name)

    # Progress
    all_categories = get_all_categories()
    made_predictions = len(predictions)
    total_categories = len(all_categories)
    st.progress(made_predictions / total_categories)
    st.write(f"**{made_predictions}** of **{total_categories}** predictions made | Showing **{len(categories)}** categories")

    # Callback for saving predictions
    def save_prediction(category_id: str, country: str):
        save_set_prediction(set_id, category_id, country)
        st.rerun()

    # Render category cards in grid
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
                        tz_name=st.session_state.timezone,
                        on_change_callback=save_prediction,
                        card_key=f"pred_{set_id}_{category.id}"
                    )


def pools_page():
    """Page for managing pools and assignments."""
    st.title("My Pools")

    # Get user's pools and prediction sets
    pools = get_user_pools(st.session_state.user_name)
    prediction_sets = get_user_prediction_sets(st.session_state.user_name)

    # Join/Create pool buttons
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("Join a Pool"):
            join_name = st.text_input("Pool Name", placeholder="Office Pool 2026", key="join_pool_name")
            if st.button("Join Pool"):
                if join_name:
                    pool = get_pool_by_name(join_name.strip())
                    if pool:
                        add_pool_member(pool['code'], st.session_state.user_name)
                        st.success(f"Joined {pool['name']}!")
                        st.rerun()
                    else:
                        st.error("Pool not found")

    with col2:
        with st.expander("Create a Pool"):
            pool_name = st.text_input("Pool Name", placeholder="Office Pool 2026", key="new_pool_name")
            if st.button("Create Pool"):
                if pool_name:
                    result = create_pool(pool_name.strip(), st.session_state.user_name)
                    if result:
                        st.success(f"Pool '{result}' created!")
                        st.rerun()
                    else:
                        st.error("A pool with that name already exists")

    st.markdown("---")

    if not pools:
        st.info("Join or create a pool to get started!")
        return

    if not prediction_sets:
        st.warning("Create a prediction set first in 'My Predictions' before assigning to pools!")
        return

    # List pools with assignment options
    st.subheader("Your Pools")

    for pool in pools:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"**{pool['name']}**")

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

    for i, user in enumerate(sorted_users[:3]):
        rank = i + 1
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "")
        is_current = user == current_user

        col1, col2 = st.columns([3, 1])
        with col1:
            name_display = f"**{user}** (you)" if is_current else user
            st.write(f"{medal} #{rank} {name_display}")
        with col2:
            st.write(f"**{scores[user]['correct']}** / {scores[user]['total']}")

    # Note about full leaderboard
    if len(sorted_users) > 3:
        st.caption(f"*{len(sorted_users) - 3} more participants - see Leaderboard tab for full standings*")

    # === YOUR PREDICTIONS ===
    st.markdown("---")
    st.subheader("Your Predictions")

    if current_user in user_predictions:
        my_predictions = user_predictions[current_user]
        made = len(my_predictions)
        total = len(categories)
        correct = scores[current_user]["correct"] if current_user in scores else 0

        st.write(f"**{made}** predictions made | **{correct}** correct so far")

        # Show user's predictions for locked categories
        locked_cats = [c for c in categories if is_category_locked(c)]
        if locked_cats:
            st.caption(f"Showing your picks for {len(locked_cats)} locked events:")

            for cat in locked_cats[:5]:  # Show first 5
                pred = my_predictions.get(cat.id, "-")
                result = results.get(cat.id)
                if result:
                    if pred == result:
                        st.write(f"✓ **{cat.display_name}**: {pred}")
                    elif pred != "-":
                        st.write(f"✗ **{cat.display_name}**: {pred} (was {result})")
                    else:
                        st.write(f"- **{cat.display_name}**: No pick (was {result})")
                else:
                    st.write(f"⏳ **{cat.display_name}**: {pred if pred != '-' else 'No pick'}")

            if len(locked_cats) > 5:
                st.caption(f"...and {len(locked_cats) - 5} more locked events")
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
    rows = []
    for cat in filtered:
        row = {"Category": cat.display_name}
        for user in data["users"]:
            row[user] = user_predictions[user].get(cat.id, "-")
        row["Result"] = results.get(cat.id, "TBD")
        rows.append(row)

    import pandas as pd
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
    st.subheader("Medal Tally")

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
        st.info("No results yet. Check back once events are completed!")

    st.markdown("---")

    # === EVENT RESULTS ===
    st.subheader("Event Results")

    if not completed:
        st.info("No events have been completed yet.")
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

    # Select pool
    pool_options = {p["code"]: p["name"] for p in pools}
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

    # Full leaderboard
    st.markdown("---")

    for i, user in enumerate(sorted_users):
        rank = i + 1
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "")
        is_current = user == current_user

        col1, col2 = st.columns([3, 1])
        with col1:
            name_display = f"**{user}** (you)" if is_current else user
            st.write(f"{medal} #{rank} {name_display}")
        with col2:
            st.write(f"**{scores[user]['correct']}** / {scores[user]['total']}")


def main():
    """Main app logic."""
    # Check if user is logged in
    if not st.session_state.user_name:
        login_page()
        return

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

    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["My Predictions", "Pools", "Leaderboard", "Results"],
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


if __name__ == "__main__":
    main()
