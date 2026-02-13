# Winter Olympics 2026 Prediction Game

## Project Overview
A Streamlit-based prediction game where users predict which countries will win the most gold medals in various Winter Olympics categories. Users can create prediction sets, join pools with friends, and compete on leaderboards.

## Design Philosophy

### Inspired by ESPN Tournament Challenge
Our design takes cues from ESPN's Tournament Challenge, the #1 bracket prediction game:

1. **Make it Easy, Fast, and Fun** - Bracket/prediction creation should be frictionless
2. **Results Tracking Should Be Insightful** - Show users how they're doing in engaging ways
3. **Social Competition** - Pools and leaderboards create engagement
4. **Quick Actions** - Offer shortcuts for users short on time

### Core UX Principles

#### Visual Hierarchy
- Most important information (scores, standings) should be immediately visible
- Use size, color, and spacing to guide the eye
- Team/country logos provide quick visual recognition
- Progress indicators show completion status at a glance

#### Clean Layouts
- Group related components visually
- Utilize white space effectively
- Uncluttered designs with focused content
- Main journey should be simple: Make Picks > Track Results > See Standings

#### Real-Time Feedback
- Immediate visual feedback when predictions are saved
- Live updates during the Olympics
- Clear status indicators (pending, correct, wrong)

#### Gamification Elements
- Leaderboards with rankings and medals for top 3
- Progress bars showing prediction completion
- Achievement indicators (streaks, perfect picks)

---

## Color Palette

### Primary Colors (Olympics-Inspired)
```
--olympic-blue: #0085C7      # Primary actions, links
--olympic-yellow: #F4C300    # Highlights, gold medals
--olympic-black: #000000     # Text, borders
--olympic-green: #009F3D     # Success states
--olympic-red: #DF0024       # Errors, warnings
```

### UI Colors
```
--background: #FFFFFF        # Main background
--surface: #F8F9FA           # Card backgrounds
--surface-elevated: #FFFFFF  # Elevated cards
--border: #E0E0E0            # Subtle borders
--border-strong: #CCCCCC     # Emphasized borders

--text-primary: #1A1A1A      # Main text
--text-secondary: #666666    # Secondary text
--text-muted: #999999        # Disabled/hint text
```

### Status Colors
```
--correct: #28A745           # Correct prediction
--wrong: #DC3545             # Wrong prediction
--pending: #6C757D           # Not yet decided
--locked: #FFC107            # Event started, can't change
```

### Gender Tag Colors
```
--tag-men: #0D6EFD           # Blue
--tag-women: #D63384         # Pink
--tag-mixed: #6F42C1         # Purple
--tag-overall: #FFC107       # Gold
```

---

## Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
```

### Scale
- **Page Title**: 32px, bold
- **Section Header**: 24px, semibold
- **Card Title**: 18px, semibold
- **Body Text**: 16px, regular
- **Caption/Meta**: 14px, regular
- **Tags/Badges**: 12px, medium

---

## Component Patterns

### Prediction Cards
Each prediction category displays as a card with:
```
+------------------------------------------+
|  [Sport Tag] [Gender Tag] [Medal Count]  |
|                                          |
|  Category Name (bold, 18px)              |
|                                          |
|  Events: Mar 6, 10:00 AM - Mar 8, 2:00 PM|
|                                          |
|  [ Country Dropdown          v ]         |
|                                          |
|  Result: Norway - Correct!  (if decided) |
+------------------------------------------+
```

**Card States:**
- Default: Light border
- Has Prediction: Subtle highlight
- Correct: Green left border
- Wrong: Red left border
- Locked: Yellow background tint

### Leaderboard
```
+------------------------------------------+
|  LEADERBOARD                             |
+------------------------------------------+
|  #1  Username           12/30 correct    |
|  #2  Username           11/30 correct    |
|  #3  Username           10/30 correct    |
|  #4  Username            9/30 correct    |
+------------------------------------------+
```

- Top 3 get medal icons
- Current user highlighted
- Show points/correct count prominently

### Progress Indicator
```
[============================--------] 75%
28 of 37 predictions made
```

### Filter Pills
```
( Sport (All) v )  ( Gender (All) v )  ( Sort v )     Delete Set
```

- Pill-shaped with rounded borders
- Compact width (max 160px)
- Clear visual grouping

### Navigation
- Sidebar navigation for main sections
- Tabs for prediction sets
- Breadcrumb-style for pool views

---

## Page Structure

### 1. Login Page
- Simple username entry
- No password (casual game)
- Welcome message for returning users

### 2. My Predictions Page
- Tabbed interface for multiple prediction sets
- Filter/sort controls
- Progress indicator
- Grid of prediction cards (3 columns)
- "Overall" category featured first

### 3. Pools Page
- List of joined pools
- Join/Create pool actions
- Prediction set assignment per pool
- Quick view buttons

### 4. Pool View / Leaderboard
- Pool name and share code
- Leaderboard with all members
- Comparison table showing everyone's picks
- Filter by sport/gender

---

## Streamlit Implementation Notes

### Session State
```python
st.session_state.user_name      # Current logged-in user
st.session_state.pool_code      # Currently viewing pool
st.session_state.current_set_id # Active prediction set
st.session_state.timezone       # User's timezone preference
```

### CSS Customization
Custom CSS is injected via `st.markdown()` with `unsafe_allow_html=True`.

Key selectors:
- `[data-testid="stSelectbox"]` - Dropdown styling
- `[data-testid="stSidebar"]` - Sidebar width
- `.stTabs` - Tab styling
- `.stProgress` - Progress bar
- `button[kind="secondary"]` - Secondary buttons

### Config File
`.streamlit/config.toml` controls:
- Theme (forced light mode)
- Server settings
- Browser settings

### Database
SQLite database (`olympics_pools.db`) with tables:
- `users` - User accounts
- `pools` - Prediction pools
- `pool_members` - Pool membership
- `prediction_sets` - Named prediction sets per user
- `predictions_v2` - Individual predictions
- `category_results` - Actual Olympic results

---

## Future Enhancements (ESPN-Inspired)

### Quick Pick Features
- **"Chalk"** - Auto-pick favorites based on historical data
- **"Random"** - Random country selection
- **"Popular"** - Pick what most users picked
- **"Smart Pick"** - AI-powered suggestions

### Enhanced Tracking
- Live results feed during Olympics
- Push notifications for results
- "Bracket Buster" alerts when upsets happen

### Social Features
- Share predictions on social media
- Compare picks with friends side-by-side
- Chat within pools

### Analytics
- Historical accuracy stats
- "Expert" picks comparison
- Medal count projections

### Gamification
- Achievements/badges
- Streak tracking
- Season-long points across events

---

## Data Model

### PredictionCategory
```python
@dataclass
class PredictionCategory:
    id: str                    # "alpine_skiing_men"
    sport: str                 # "Alpine Skiing"
    gender: str | None         # "Men", "Women", "Mixed", None
    display_name: str          # "Men's Alpine Skiing"
    event_count: int           # Number of gold medals
    first_event_date: datetime # When events start
    last_event_date: datetime  # When events end
    is_overall: bool           # True for "Most Gold Medals Overall"
```

### Sports Categories
- Alpine Skiing (Men, Women)
- Biathlon (Men, Women, Mixed)
- Bobsled (Men, Women, Mixed)
- Cross-Country Skiing (Men, Women)
- Curling (Men, Women, Mixed)
- Figure Skating (Men, Women, Mixed)
- Freestyle Skiing (Men, Women)
- Ice Hockey (Men, Women)
- Luge (Men, Women, Mixed)
- Nordic Combined (Men)
- Short Track (Men, Women, Mixed)
- Skeleton (Men, Women)
- Ski Jumping (Men, Women, Mixed)
- Snowboard (Men, Women)
- Speed Skating (Men, Women)
- **Overall** (all medals combined)

---

## Scraping Olympics.com

**Olympics.com uses Akamai CDN with aggressive bot protection.** Standard HTTP tools (Python `requests`, `WebFetch`) will get 403 errors due to TLS fingerprinting.

**Always use curl** (via subprocess or Bash) with full browser headers to fetch Olympics.com pages:

```bash
curl -sL \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Accept-Encoding: identity" \
  -H "Sec-Fetch-Dest: document" \
  -H "Sec-Fetch-Mode: navigate" \
  -H "Sec-Fetch-Site: none" \
  "https://www.olympics.com/en/milano-cortina-2026/..."
```

Or use the `_curl_fetch()` helper in `scraper.py` from Python:
```python
from scraper import _curl_fetch
html = _curl_fetch("https://www.olympics.com/en/milano-cortina-2026/schedule/short-track-speed-skating")
```

**Key data pages:**
- Medal standings: `/en/milano-cortina-2026/medals` — JSON in `"medalStandings"` key
- Individual medalists: `/en/milano-cortina-2026/medals/medallists` — JSON in `result_medallists_data` inside a `<script>` tag
- Sport schedules: `/en/milano-cortina-2026/schedule/{sport-slug}` — embedded JSON schedule data

---

## Resources

### Design Inspiration
- [ESPN Tournament Challenge](https://fantasy.espn.com/games/tournament-challenge-bracket-2025/)
- [ESPN Tournament Challenge Redesign (2024)](https://www.espnfrontrow.com/2024/03/how-espn-has-reimagined-redesigned-rebuilt-tournament-challenge/)
- [Sports Betting App UX Guide](https://prometteursolutions.com/blog/user-experience-and-interface-in-sports-betting-apps/)

### Technical
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Streamlit Custom CSS](https://docs.streamlit.io/library/api-reference/utilities/st.markdown)

---

## Running the App

### Local Development
```bash
# Activate environment
conda activate winter_olympics

# Run the app
cd winter_olympics_game
streamlit run app.py

# View at http://localhost:8501
```

### Deployment (Streamlit Cloud)
1. Push code to GitHub
2. Connect repo to Streamlit Cloud
3. Deploy with `.streamlit/config.toml` for settings
4. Note: Free tier apps sleep after inactivity (wake-up delay expected)
