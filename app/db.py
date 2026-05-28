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
    Adds a purchased meal to the purchases collection.
    This is used when a user clicks Purchase on the Browse Meals page.
    """
    if purchase_date is None:
        purchase_date = date.today().isoformat()

    purchase = {
        "meal_name": meal_name,
        "dining_hall": dining_hall,
        "meal_type": meal_type,
        "point_value": float(point_value),
        "purchase_date": purchase_date,
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
    Deletes a purchase from the purchases collection.
    """
    return purchases_col.delete_one({"_id": ObjectId(purchase_id)})


# ── Budget Management ─────────────────────────────
def set_budget(amount):
    """
    Sets or updates the meal points budget (global, single user).
    """
    users_col.update_one(
        {"_id": "budget"},
        {"$set": {"amount": float(amount)}},
        upsert=True
    )

def get_budget():
    """
    Gets the current meal points budget (global, single user).
    """
    doc = users_col.find_one({"_id": "budget"})
    return doc["amount"] if doc and "amount" in doc else None

def get_remaining_budget():
    """
    Returns the remaining budget (budget - total spent).
    """
    budget = get_budget()
    spent = get_total_spent()
    if budget is None:
        return None
    return budget - spent