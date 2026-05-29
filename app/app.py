from flask import Flask, render_template, request, redirect, url_for, flash
from db import (
    meal_options_col,
    add_purchase,
    get_all_purchases,
    add_purchase_again,
    delete_purchase,
    set_budget,
    get_budget,
    get_total_spent,
    get_remaining_budget,
    get_points_to_spend_before_reset,
    check_weekly_reset,
    force_weekly_reset
)
import csv
import io

app = Flask(__name__)
app.secret_key = "mealtrack-dev-secret"

# ── Browse Meals ──────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    check_weekly_reset()

    budget = get_budget()
    total_spent = get_total_spent()
    remaining = get_remaining_budget()
    points_to_spend = get_points_to_spend_before_reset()

    return render_template(
        "dashboard.html",
        budget=budget,
        total_spent=total_spent,
        remaining=remaining,
        points_to_spend=points_to_spend
    )

@app.route("/test-reset")
def test_reset():
    force_weekly_reset()
    flash("Weekly reset forced for testing.", "success")
    return redirect(url_for("dashboard"))


# ── Budget Form Submission ───────────────────────
@app.route("/set-budget", methods=["POST"])
def set_budget_route():
    plan_name = request.form.get("plan_name", "").strip()
    current_points = request.form.get("current_points", "").strip()
    rollover_points = request.form.get("rollover_points", "0").strip()

    try:
        current_points = float(current_points)
        rollover_points = float(rollover_points)

        if current_points < 0 or rollover_points < 0:
            raise ValueError

        set_budget(plan_name, current_points, rollover_points)
        flash("Budget updated.", "success")

    except ValueError:
        flash("Please enter a valid meal plan and non-negative point values.", "error")

    return redirect(url_for("dashboard"))

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

@app.route("/meals/log", methods=["POST"])
def meal_log():
    item_name   = request.form.get("item_name", "").strip()
    point_cost  = request.form.get("point_cost", "").strip()
    location    = request.form.get("location", "").strip()
    meal_type   = request.form.get("meal_type", "").strip()

    try:
        point_cost = float(point_cost)
    except ValueError:
        flash("Point cost must be a number.", "error")
        return redirect(url_for("meals"))

    purchase_id = add_purchase(item_name, location, point_cost, meal_type)

    if purchase_id is None:
        flash("You do not have enough weekly or rollover points to add this meal.", "error")
        return redirect(url_for("meals"))

    flash(f"{item_name} logged to purchase history.", "success")
    return redirect(url_for("meals"))

# ── CSV Upload (for teammate to hook into settings) ───────────────────────────

@app.route("/meals/upload", methods=["POST"])
def meal_upload():
    file = request.files.get("csv_file")
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("settings"))
    if not file.filename.lower().endswith(".csv"):
        flash("Invalid file type. Please upload a .csv file.", "error")
        return redirect(url_for("settings"))

    stream  = io.StringIO(file.stream.read().decode("utf-8"))
    reader  = csv.DictReader(stream)
    expected_headers = ["meal_name", "point_value", "meal_type", "dining_hall"]
    received_headers = [h for h in (reader.fieldnames or [])]

    if received_headers != expected_headers:
        flash(
            "Invalid CSV headers. Required exact order (with no spaces): "
            "meal_name,point_value,meal_type,dining_hall",
            "error"
        )
        return redirect(url_for("settings"))

    added   = 0
    skipped = 0

    for row in reader:
        try:
            # print(f"row: {row}", flush=True)
            meal_name   = row.get("meal_name", "")
            point_value = row.get("point_value", "")
            meal_type   = row.get("meal_type", "")
            dining_hall = row.get("dining_hall", "")

            if not meal_name or not dining_hall or not point_value or not meal_type:
                skipped += 1
                continue

            meal_name = meal_name.strip()
            point_value = point_value.strip()
            meal_type = meal_type.strip()
            dining_hall = dining_hall.strip()

            try:
                point_value = float(point_value)
            except ValueError:
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
        except Exception as e:
            print(f"Error: {e}", flush=True)
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
        flash("Purchase could not be added again. There may not be enough points.", "error")
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