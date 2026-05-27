from flask import Flask, render_template, request, redirect, url_for, flash
from db import (
    meal_options_col,
    add_purchase,
    get_all_purchases,
    add_purchase_again,
    delete_purchase
)
import csv
import io

app = Flask(__name__)
app.secret_key = "mealtrack-dev-secret"

# ── Browse Meals ──────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/meals")
def meals():
    dining_hall = request.args.get("dining_hall", "")
    meal_type   = request.args.get("meal_type", "")

    query = {}
    if dining_hall:
        query["dining_hall"] = dining_hall
    if meal_type:
        query["meal_type"] = meal_type

    items       = list(meal_options_col.find(query, {"_id": 0}))
    dining_halls = meal_options_col.distinct("dining_hall")
    meal_types   = meal_options_col.distinct("meal_type")

    return render_template("meals.html", items=items,
                           dining_halls=dining_halls, meal_types=meal_types,
                           selected_hall=dining_hall, selected_type=meal_type)

@app.route("/meals/add", methods=["POST"])
def meal_add():
    meal_name   = request.form.get("meal_name", "").strip()
    point_value = request.form.get("point_value", "").strip()
    meal_type   = request.form.get("meal_type", "").strip()
    dining_hall = request.form.get("dining_hall", "").strip()

    if not meal_name or not point_value or not meal_type or not dining_hall:
        flash("All fields are required.", "error")
        return redirect(url_for("meals"))

    try:
        point_value = float(point_value)
    except ValueError:
        flash("Point value must be a number.", "error")
        return redirect(url_for("meals"))

    meal_options_col.update_one(
        {"meal_name": meal_name, "dining_hall": dining_hall},
        {"$set": {
            "meal_name":   meal_name,
            "point_value": point_value,
            "meal_type":   meal_type,
            "dining_hall": dining_hall,
        }},
        upsert=True
    )
    flash(f"{meal_name} added successfully.", "success")
    return redirect(url_for("meals"))

# ── CSV Upload (for teammate to hook into settings) ───────────────────────────

@app.route("/meals/upload", methods=["POST"])
def meal_upload():
    file = request.files.get("csv_file")
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("settings"))

    stream  = io.StringIO(file.stream.read().decode("utf-8"))
    reader  = csv.DictReader(stream)
    added   = 0
    skipped = 0

    for row in reader:
        try:
            meal_name   = row["meal_name"].strip()
            point_value = float(row["point_value"].strip())
            meal_type   = row["meal_type"].strip()
            dining_hall = row["dining_hall"].strip()

            if not meal_name or not dining_hall:
                skipped += 1
                continue

            meal_options_col.update_one(
                {"meal_name": meal_name, "dining_hall": dining_hall},
                {"$set": {
                    "meal_name":   meal_name,
                    "point_value": point_value,
                    "meal_type":   meal_type,
                    "dining_hall": dining_hall,
                }},
                upsert=True
            )
            added += 1
        except (KeyError, ValueError):
            skipped += 1

    flash(f"Upload complete — {added} meals added/updated, {skipped} rows skipped.", "success")
    return redirect(url_for("settings"))

# ── Other pages ───────────────────────────────────────────────────────────────

@app.route("/history")
def history():
    purchases = get_all_purchases()
    total_spent = sum(purchase["point_value"] for purchase in purchases)

    return render_template(
        "history.html",
        purchases=purchases,
        total_spent=total_spent
    )


@app.route("/history/add-again/<purchase_id>", methods=["POST"])
def add_history_item_again(purchase_id):
    new_purchase_id = add_purchase_again(purchase_id)

    if new_purchase_id is None:
        flash("Purchase could not be found.", "error")
    else:
        flash("Purchase added again with today's date.", "success")

    return redirect(url_for("history"))


@app.route("/history/delete/<purchase_id>", methods=["POST"])
def delete_history_item(purchase_id):
    delete_purchase(purchase_id)
    flash("Purchase deleted.", "success")
    return redirect(url_for("history"))

@app.route("/settings")
def settings():
    return render_template("settings.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)