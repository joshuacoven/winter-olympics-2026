# "What to Root For" Tab Implementation

## Summary

Implemented a new tab on the Results page that shows users which upcoming events matter for their predictions and what needs to happen for them to win each category.

## Files Created

### `/winter_olympics_game/rooting.py`
Core logic module containing:

**Data Models:**
- `CategoryStanding` - Current medal standings for a category
- `RootingInfo` - Information about what to root for

**Main Functions:**
- `get_rooting_info_for_user(prediction_set_id)` - Main entry point that returns sorted list of rooting recommendations
- `calculate_category_standing(category)` - Calculates current standings and remaining events
- `is_prediction_still_possible(standing, prediction, category)` - Determines if a prediction can still win
- `get_remaining_events_for_category(category, standing)` - Gets list of upcoming events
- `generate_scenarios(standing, prediction, category)` - Creates human-readable scenario descriptions
- `calculate_urgency(events)` - Determines urgency level (today/this_week/later)

**Event Matching:**
- Reuses fuzzy matching logic from app.py to match completed events with event definitions

## Files Modified

### `/winter_olympics_game/app.py`

**Added Import:**
```python
from rooting import get_rooting_info_for_user, RootingInfo
```

**Modified Tab Definition (line ~1064):**
Added 4th tab "What to Root For" to results page

**New Tab Content (after line ~1349):**
- Shows message for non-logged-in users
- Dropdown to select prediction set
- Summary stats (active predictions vs eliminated)
- 3 sections:
  1. 🔥 High Priority (today/this week) - expanded by default
  2. 📅 Coming Up Later - collapsed expanders
  3. ❌ Eliminated - collapsed by default

**New Helper Functions:**
- `_flag_for_country(country_name)` - Converts country name to flag emoji
- `_render_rooting_card(info, user_tz)` - Renders high-priority rooting card
- `_render_rooting_detail(info, user_tz)` - Renders detailed info in expander

## Features

### Smart Scenario Generation
- **Leading:** "✅ Leading! Stay ahead to win."
- **Tied:** "🤝 Tied for lead! Win any remaining event..."
- **Behind but possible:** "📈 Need [country] to win X more golds than [leader]."
- **Eliminated:** "❌ Mathematically eliminated"

### Urgency Levels
- **Today:** Events happening today
- **This Week:** Events within 7 days
- **Later:** Events beyond 7 days

### Special Handling
- **Prop Bets:** Shows custom messages for yes/no and numeric predictions
- **Overall Category:** Shows only next 10 events (to avoid overwhelming list)
- **Ties:** Properly handles multiple countries tied for lead

### Edge Cases Handled
1. Tied medal counts - shows "Norway, Sweden" as leader
2. Prop bets (yes/no, numeric) - custom scenario text
3. Overall category - limits to 10 next events
4. No remaining events but incomplete - skips category
5. Event matching - fuzzy matching handles name variations

## Testing

Created `/winter_olympics_game/test_rooting.py` with tests for:
- Event name matching
- Urgency calculation
- Category standing calculation
- Scenario generation

All tests pass ✅

## Example Output

### High Priority Card
```
### Alpine Skiing
**Your Pick:** 🇳🇴 Norway
Current leader: Switzerland

📈 Need Norway to win 2 more golds than Switzerland.

📅 **Next Event:** Feb 18, 5:00 AM EST — Women's Slalom
```

### Eliminated Card
```
**Alpine Skiing** — Your pick: 🇺🇸 United States
❌ Mathematically eliminated — Switzerland has too many golds.
```

## Verification Checklist

- [x] Tab exists on Results page
- [x] Shows appropriate message for logged-out users
- [x] Shows message when no predictions exist
- [x] Active predictions display correctly
- [x] High priority section shows today/this week events
- [x] Later section shows future events in expanders
- [x] Eliminated section shows impossible predictions (collapsed)
- [x] Calculations are correct (leading, behind, eliminated)
- [x] Event timing shows in user's timezone
- [x] Sport categories work
- [x] Featured categories handled
- [x] Overall category handled
- [x] Flags display correctly
- [x] Syntax errors checked
- [x] Logic tests pass

## Performance

- Leverages existing Streamlit caching from scraper functions
- No additional database queries beyond existing prediction loading
- Event matching is efficient (O(n*m) where n=events, m=completed)

## Next Steps (Optional Enhancements)

1. Add countdown timers for events happening today
2. Show live score updates during events
3. Add ability to filter by sport
4. Show probability calculations for scenarios
5. Add notifications when key events start
