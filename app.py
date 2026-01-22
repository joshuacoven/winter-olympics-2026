"""
Winter Olympics 2026 Prediction Game

A Streamlit app for friends to predict gold medal winners and compete.
"""

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

from categories import get_all_categories, get_sports_list, get_countries, PredictionCategory
from database import (
    create_pool, get_pool, pool_exists, create_user, user_exists,
    get_user_pools, add_pool_member, is_pool_admin,
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

# Custom CSS
st.markdown("""
<style>
    /* Reduce sidebar width */
    [data-testid="stSidebar"] {
        min-width: 200px;
        max-width: 280px;
    }
    /* Style vertical tabs */
    .stRadio > div {
        flex-direction: column;
        gap: 0;
    }
    .stRadio > div > label {
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 4px;
        transition: background-color 0.2s;
    }
    .stRadio > div > label:hover {
        background-color: rgba(151, 166, 195, 0.15);
    }
    .stRadio > div > label > div:first-child {
        display: none;
    }
    /* Keep pointer cursor on selectbox until clicked */
    [data-testid="stSelectbox"],
    [data-testid="stSelectbox"] * {
        cursor: pointer !important;
    }
    /* Hide "Press Enter to apply" helper text */
    .stTextInput div[data-testid="InputInstructions"] {
        display: none;
    }
    /* Pill-style dropdowns - smaller width */
    [data-testid="stSelectbox"] {
        max-width: 160px;
    }
    [data-testid="stSelectbox"] > div > div {
        border-radius: 25px;
        border: 1px solid #ccc;
        background-color: white;
        padding: 2px 12px;
        min-height: 38px;
    }
    /* Style Delete Set button as plain text, right-aligned */
    button[kind="secondary"] {
        background: none !important;
        border: none !important;
        color: #666;
        font-weight: normal;
        padding: 0;
        float: right;
    }
    button[kind="secondary"]:hover {
        background: none !important;
        border: none !important;
        color: #333;
    }
    /* Vertical spacing - tabs */
    .stTabs [data-baseweb="tab-list"] {
        margin-bottom: 24px;
    }
    /* Vertical spacing - after filter row */
    .stProgress {
        margin-top: 24px;
    }
    /* Vertical spacing - prediction cards */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        margin-bottom: 16px;
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
    # Determine status styling
    if result:
        if prediction and prediction == result:
            border_color = "#28a745"
            status_text = "Correct!"
            status_color = "#28a745"
        elif prediction:
            border_color = "#dc3545"
            status_text = "Wrong"
            status_color = "#dc3545"
        else:
            border_color = "#6c757d"
            status_text = "No prediction"
            status_color = "#6c757d"
    else:
        border_color = "#3d5a80"
        status_text = None
        status_color = None

    # Gender tag colors
    gender_colors = {"Men": "#0d6efd", "Women": "#d63384", "Mixed": "#6f42c1", None: "#ffc107"}
    gender_color = gender_colors.get(category.gender, "#6c757d")

    with st.container(border=True):
        # Category name
        st.markdown(f"**{category.display_name}**")

        # Tags
        if category.is_overall:
            st.markdown(
                f'<span style="background-color: #ffc107; color: #000; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em;">{category.event_count} gold medals</span>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<span style="background-color: #2c3e50; color: #fff; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em; margin-right: 6px;">{category.sport}</span>'
                f'<span style="background-color: {gender_color}; color: white; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em; margin-right: 6px;">{category.gender}</span>'
                f'<span style="background-color: #6c757d; color: white; padding: 2px 8px; '
                f'border-radius: 10px; font-size: 0.75em;">{category.event_count} golds</span>',
                unsafe_allow_html=True
            )

        # Date range
        if category.first_event_date and category.last_event_date:
            st.caption(
                f"**Events:** {format_datetime(category.first_event_date, tz_name)} - "
                f"{format_datetime(category.last_event_date, tz_name)}"
            )

        # Prediction dropdown
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

    st.subheader("Log In")
    with st.form("login"):
        username = st.text_input("Username", placeholder="Enter your username")
        submitted = st.form_submit_button("Log In")

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
                key="first_set_name_input"
            )
        with col2:
            st.write("")  # Spacing
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
                key="new_set_name_input"
            )
        with col2:
            st.write("")  # Spacing
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
            join_code = st.text_input("Pool Code", placeholder="ABC123", key="join_code").upper()
            if st.button("Join Pool"):
                if join_code and pool_exists(join_code):
                    add_pool_member(join_code, st.session_state.user_name)
                    st.success("Joined pool!")
                    st.rerun()
                elif join_code:
                    st.error("Pool not found")

    with col2:
        with st.expander("Create a Pool"):
            pool_name = st.text_input("Pool Name", placeholder="Office Pool 2026", key="new_pool_name")
            if st.button("Create Pool"):
                if pool_name:
                    code = create_pool(pool_name, st.session_state.user_name)
                    st.success(f"Pool created! Code: **{code}**")
                    st.rerun()

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
                st.caption(f"Code: `{pool['code']}`")

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


def pool_view_page():
    """View a specific pool's predictions."""
    pool = get_pool(st.session_state.pool_code)
    if not pool:
        st.error("Pool not found")
        return

    st.title(f"Pool: {pool['name']}")
    st.caption(f"Code: `{pool['code']}`")

    if st.button("Back to My Pools"):
        st.session_state.view_pool = False
        st.rerun()

    st.markdown("---")

    # Get all assignments for this pool
    assignments = get_pool_assignments_for_pool(pool['code'])

    if not assignments:
        st.info("No one has assigned predictions to this pool yet.")
        return

    # Get all categories and results
    categories = get_all_categories()
    results = get_category_results()

    # Build comparison data
    users = sorted(assignments.keys())
    user_predictions = {}
    for user, set_id in assignments.items():
        user_predictions[user] = get_predictions_for_set(set_id)

    # Calculate scores
    scores = {}
    for user in users:
        correct = sum(
            1 for cat in categories
            if cat.id in results and user_predictions[user].get(cat.id) == results[cat.id]
        )
        total = len(user_predictions[user])
        scores[user] = {"correct": correct, "total": total}

    # Display leaderboard
    st.subheader("Leaderboard")
    sorted_users = sorted(users, key=lambda u: scores[u]["correct"], reverse=True)

    for i, user in enumerate(sorted_users):
        rank = i + 1
        medal = ""
        if rank == 1:
            medal = " 🥇"
        elif rank == 2:
            medal = " 🥈"
        elif rank == 3:
            medal = " 🥉"

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**#{rank}** {user}{medal}")
        with col2:
            st.write(f"**{scores[user]['correct']}** / {scores[user]['total']}")

    st.markdown("---")

    # Comparison table
    st.subheader("Predictions Comparison")

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

    # Apply filters
    filtered_categories = categories
    if sport_filter != "All":
        filtered_categories = [c for c in filtered_categories if c.sport == sport_filter]
    if gender_filter != "All":
        filtered_categories = [c for c in filtered_categories if c.gender == gender_filter]

    # Build table data
    rows = []
    for cat in filtered_categories:
        row = {"Category": cat.display_name, "Sport": cat.sport}
        for user in users:
            row[user] = user_predictions[user].get(cat.id, "-")
        row["Result"] = results.get(cat.id, "TBD")
        rows.append(row)

    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


def leaderboard_page():
    """Global leaderboard across pools user is in."""
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
    pool_view_page()


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
        ["My Predictions", "Pools", "Leaderboard"],
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")

    if st.sidebar.button("Log Out", use_container_width=True):
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


if __name__ == "__main__":
    main()
