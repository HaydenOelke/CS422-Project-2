import os
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/mealtrack")

client = MongoClient(MONGO_URI)
db = client.get_default_database()

meal_options_col = db["meal_options"]
users_col        = db["users"]
purchases_col    = db["purchases"]
