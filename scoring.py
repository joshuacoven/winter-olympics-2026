"""
Scoring calculations for the Winter Olympics Prediction Game.
"""

from database import get_all_predictions, get_results, get_pool_participants


def calculate_scores(pool_code: str) -> list[dict]:
    """
    Calculate scores for all participants in a pool.

    Returns list of dicts with:
        - user_name: participant name
        - correct: number of correct predictions
        - total_predicted: total predictions made
        - total_results: total results entered so far

    Sorted by correct predictions (descending), then by name.
    """
    predictions = get_all_predictions(pool_code)
    results = get_results(pool_code)
    participants = get_pool_participants(pool_code)

    scores = []

    for user in participants:
        user_preds = predictions.get(user, {})
        correct = 0

        # Count correct predictions
        for event_id, predicted_country in user_preds.items():
            if event_id in results and results[event_id] == predicted_country:
                correct += 1

        scores.append({
            "user_name": user,
            "correct": correct,
            "total_predicted": len(user_preds),
            "total_results": len(results)
        })

    # Sort by correct (desc), then by name (asc)
    scores.sort(key=lambda x: (-x["correct"], x["user_name"]))

    return scores


def get_user_score_details(pool_code: str, user_name: str) -> list[dict]:
    """
    Get detailed scoring breakdown for a user.

    Returns list of dicts with:
        - event_id: event identifier
        - prediction: user's prediction (or None)
        - result: actual result (or None if not yet entered)
        - correct: True/False/None (None if no result yet)
    """
    from database import get_user_predictions

    predictions = get_user_predictions(pool_code, user_name)
    results = get_results(pool_code)

    details = []

    # Get all events the user predicted
    all_event_ids = set(predictions.keys()) | set(results.keys())

    for event_id in sorted(all_event_ids):
        pred = predictions.get(event_id)
        result = results.get(event_id)

        if result is not None and pred is not None:
            correct = pred == result
        else:
            correct = None

        details.append({
            "event_id": event_id,
            "prediction": pred,
            "result": result,
            "correct": correct
        })

    return details
