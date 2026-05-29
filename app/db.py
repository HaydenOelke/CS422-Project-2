import os
from pymongo import MongoClient
from datetime import datetime, date
from bson.objectid import ObjectId

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/mealtrack")

client = MongoClient(MONGO_URI)
db = client.get_default_database()

meal_options_col = db["meal_options"]
users_col        = db["users"]
purchases_col    = db["purchases"]

def add_purchase(meal_name, dining_hall, point_value, meal_type="", purchase_date=None):
    """
    Adds a purchased meal to the purchases collection only if enough points are available.
    Weekly points are used first, then rollover points.
    """
    if purchase_date is None:
        purchase_date = date.today().isoformat()

    point_value = float(point_value)

    point_usage = subtract_points(point_value)

    if point_usage is None:
        return None

    purchase = {
        "meal_name": meal_name,
        "dining_hall": dining_hall,
        "meal_type": meal_type,
        "point_value": point_value,
        "purchase_date": purchase_date,
        "weekly_points_used": point_usage["weekly_used"],
        "rollover_points_used": point_usage["rollover_used"],
        "created_at": datetime.utcnow()
    }

    result = purchases_col.insert_one(purchase)
    return str(result.inserted_id)


def get_all_purchases():
    """
    Returns all purchases sorted by most recent date.
    """
    purchases = purchases_col.find().sort("purchase_date", -1)

    purchase_list = []
    for purchase in purchases:
        purchase["_id"] = str(purchase["_id"])
        purchase_list.append(purchase)

    return purchase_list


def get_total_spent():
    """
    Returns the total number of points spent across all purchases.
    Dashboard can use this.
    """
    purchases = get_all_purchases()
    return sum(purchase["point_value"] for purchase in purchases)

def get_total_spent_this_week():
    """
    Returns the total number of points spent during the current week.
    The week starts on Sunday, because meal points reset Sunday morning.
    """
    today = date.today()

    # Python weekday: Monday = 0, Sunday = 6
    # This calculates the most recent Sunday.
    days_since_sunday = (today.weekday() + 1) % 7
    sunday = today.fromordinal(today.toordinal() - days_since_sunday)

    purchases = purchases_col.find({
        "purchase_date": {"$gte": sunday.isoformat()}
    })

    return sum(float(purchase.get("point_value", 0)) for purchase in purchases)

def get_days_left_in_week():
    """
    Returns the number of days left before the next Sunday reset.
    Sunday counts as 7 because the weekly points just reset.
    """
    today = date.today()

    # Python weekday: Monday = 0, Sunday = 6
    days_since_sunday = (today.weekday() + 1) % 7
    days_left = 7 - days_since_sunday

    return max(days_left, 1)


def get_average_points_per_day():
    """
    Returns the average number of points available per day
    based on the days left before Sunday reset.
    """
    remaining = get_remaining_budget()

    if remaining is None:
        return None

    days_left = get_days_left_in_week()

    return round(remaining / days_left)

def get_purchase_by_id(purchase_id):
    """
    Gets one purchase by its MongoDB id.
    """
    purchase = purchases_col.find_one({"_id": ObjectId(purchase_id)})

    if purchase:
        purchase["_id"] = str(purchase["_id"])

    return purchase


def add_purchase_again(purchase_id):
    """
    Copies an old purchase and adds it again with today's date.
    """
    old_purchase = get_purchase_by_id(purchase_id)

    if not old_purchase:
        return None

    return add_purchase(
        meal_name=old_purchase["meal_name"],
        dining_hall=old_purchase["dining_hall"],
        point_value=old_purchase["point_value"],
        meal_type=old_purchase.get("meal_type", ""),
        purchase_date=date.today().isoformat()
    )


def delete_purchase(purchase_id):
    """
    Deletes a purchase and restores the points that were used for it.
    """
    purchase = get_purchase_by_id(purchase_id)

    if not purchase:
        return None

    result = purchases_col.delete_one({"_id": ObjectId(purchase_id)})

    if result.deleted_count == 1:
        add_points(
            weekly_points_used=purchase.get("weekly_points_used", purchase.get("point_value", 0)),
            rollover_points_used=purchase.get("rollover_points_used", 0)
        )

    return result

# ── Budget Management ─────────────────────────────
PLAN_OPTIONS = {
    "Deluxe": 95,
    "Standard": 80,
    "Select": 65,
    "Mini": 50,
    "Carson-based": 5
}

ROLLOVER_LIMIT = 50


def get_budget_doc():
    """
    Gets the global single-user budget document.
    """
    return users_col.find_one({"_id": "budget"})


def set_budget(plan_name, current_points=0, rollover_points=0):
    """
    Sets or updates the selected meal plan and current point balance.
    """
    plan_points = PLAN_OPTIONS.get(plan_name)

    if plan_points is None:
        raise ValueError("Invalid meal plan selected.")

    users_col.update_one(
        {"_id": "budget"},
        {
            "$set": {
                "plan_name": plan_name,
                "plan_points": float(plan_points),
                "current_points": float(current_points),
                "rollover_points": float(rollover_points),
                "last_reset_date": None,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )


def get_budget():
    """
    Gets the current budget document.
    """
    return get_budget_doc()


def subtract_points(point_value):
    """
    Subtracts points from the weekly points first, then rollover points.
    Returns a dictionary describing how many points were used from each bucket.
    Returns None if there are not enough points.
    """
    point_value = float(point_value)
    budget = get_budget_doc()

    if not budget:
        return None

    current_points = float(budget.get("current_points", 0))
    rollover_points = float(budget.get("rollover_points", 0))

    total_available = current_points + rollover_points

    if point_value > total_available:
        return None

    weekly_used = min(current_points, point_value)
    rollover_used = point_value - weekly_used

    new_current_points = current_points - weekly_used
    new_rollover_points = rollover_points - rollover_used

    users_col.update_one(
        {"_id": "budget"},
        {
            "$set": {
                "current_points": new_current_points,
                "rollover_points": new_rollover_points,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "weekly_used": weekly_used,
        "rollover_used": rollover_used
    }


def add_points(weekly_points_used=0, rollover_points_used=0):
    """
    Adds points back to the same buckets they were originally spent from.
    This is used when a purchase is deleted.
    """
    users_col.update_one(
        {"_id": "budget"},
        {
            "$inc": {
                "current_points": float(weekly_points_used),
                "rollover_points": float(rollover_points_used)
            },
            "$set": {"updated_at": datetime.utcnow()}
        }
    )


def check_weekly_reset():
    """
    Checks whether today is Sunday and resets the weekly points if needed.
    The reset only happens once per Sunday.
    """
    today = date.today()
    budget = get_budget_doc()

    if not budget:
        return None

    # Python weekday: Monday = 0, Sunday = 6
    is_sunday = today.weekday() == 6
    already_reset_today = budget.get("last_reset_date") == today.isoformat()

    if not is_sunday or already_reset_today:
        return budget

    current_points = float(budget.get("current_points", 0))
    plan_points = float(budget.get("plan_points", 0))

    rollover_points = min(current_points, ROLLOVER_LIMIT)
    new_current_points = plan_points + rollover_points

    users_col.update_one(
        {"_id": "budget"},
        {
            "$set": {
                "rollover_points": rollover_points,
                "current_points": new_current_points,
                "last_reset_date": today.isoformat(),
                "updated_at": datetime.utcnow()
            }
        }
    )

    return get_budget_doc()

def force_weekly_reset():
    """
    Forces the weekly reset immediately.
    Used only for testing.
    """
    today = date.today()
    budget = get_budget_doc()

    if not budget:
        return None

    current_points = float(budget.get("current_points", 0))
    plan_points = float(budget.get("plan_points", 0))

    rollover_points = min(current_points, ROLLOVER_LIMIT)
    new_current_points = plan_points

    users_col.update_one(
        {"_id": "budget"},
        {
            "$set": {
                "rollover_points": rollover_points,
                "current_points": new_current_points,
                "last_reset_date": today.isoformat(),
                "updated_at": datetime.utcnow()
            }
        }
    )

    return get_budget_doc()


def get_points_to_spend_before_reset():
    """
    Calculates how many points need to be spent before Sunday
    so the user does not lose points over the rollover limit.
    """
    budget = get_budget_doc()

    if not budget:
        return None

    weekly_points_left = float(budget.get("current_points", 0))
    rollover_points_left = float(budget.get("rollover_points", 0))

    total_points_that_could_rollover = weekly_points_left + rollover_points_left

    return max(0, total_points_that_could_rollover - ROLLOVER_LIMIT)


def get_remaining_budget():
    """
    Returns the total points available, including weekly and rollover points.
    """
    budget = get_budget_doc()

    if not budget:
        return None

    current_points = float(budget.get("current_points", 0))
    rollover_points = float(budget.get("rollover_points", 0))

    return current_points + rollover_points