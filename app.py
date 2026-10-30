import os
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # lets matplotlib draw charts without opening a window
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, render_template, request, redirect, url_for, flash, send_file

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # needed for flash messages

DATA_FILE = "data/expenses.csv"
CHART_FOLDER = "static/charts"
CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Health", "Entertainment", "Other"]
COLUMNS = ["date", "category", "amount", "description"]

# Create folders and an empty CSV the first time the app runs
os.makedirs("data", exist_ok=True)
os.makedirs(CHART_FOLDER, exist_ok=True)

if not os.path.exists(DATA_FILE):
    empty_df = pd.DataFrame(columns=COLUMNS)
    empty_df.to_csv(DATA_FILE, index=False)


# ---------------- HOME ----------------
@app.route("/")
def home():
    df = pd.read_csv(DATA_FILE)
    total = df["amount"].sum()
    count = len(df)
    recent = df.tail(5).iloc[::-1].to_dict(orient="records")  # last 5, newest first
    return render_template("index.html", total=total, count=count, recent=recent)


# ---------------- ADD EXPENSE ----------------
@app.route("/add", methods=["GET", "POST"])
def add_expense():
    if request.method == "POST":
        date = request.form["date"]
        category = request.form["category"]
        amount = request.form["amount"]
        description = request.form["description"]

        if date == "" or amount == "":
            flash("Date and amount are required.")
            return redirect(url_for("add_expense"))

        if description == "":
            description = "-"

        df = pd.read_csv(DATA_FILE)
        df.loc[len(df)] = [date, category, float(amount), description]  # add new row at the end
        df.to_csv(DATA_FILE, index=False)

        flash("Expense added!")
        return redirect(url_for("view_expenses"))

    today = datetime.today().strftime("%Y-%m-%d")
    return render_template("add.html", categories=CATEGORIES, today=today)


# ---------------- VIEW / FILTER EXPENSES ----------------
@app.route("/expenses")
def view_expenses():
    df = pd.read_csv(DATA_FILE)
    df["row_id"] = df.index  # remember the original row number (used for delete)

    selected = request.args.get("category", "All")
    if selected != "All":
        df = df[df["category"] == selected]

    df = df.sort_values("date", ascending=False)
    total = df["amount"].sum()
    expenses = df.to_dict(orient="records")

    return render_template("expenses.html", expenses=expenses, categories=CATEGORIES,
                           selected=selected, total=total)


# ---------------- DELETE EXPENSE ----------------
@app.route("/delete/<int:row_id>", methods=["POST"])
def delete_expense(row_id):
    df = pd.read_csv(DATA_FILE)
    df = df.drop(row_id)
    df.to_csv(DATA_FILE, index=False)
    flash("Expense deleted.")
    return redirect(url_for("view_expenses"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    df = pd.read_csv(DATA_FILE)

    if df.empty:
        flash("Add some expenses first to see the dashboard.")
        return redirect(url_for("add_expense"))

    # Pandas: convert dates and make a "month" column like 2026-10
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")

    # NumPy: statistics
    amounts = df["amount"].to_numpy()
    stats = {
        "total": np.sum(amounts),
        "average": np.mean(amounts),
        "median": np.median(amounts),
        "highest": np.max(amounts),
        "lowest": np.min(amounts),
        "std": np.std(amounts),
    }

    # Pandas: group totals
    category_totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    monthly_totals = df.groupby("month")["amount"].sum()
    top_category = category_totals.index[0]

    # Chart 1: Pie chart (Matplotlib)
    plt.figure(figsize=(6, 6))
    plt.pie(category_totals.values, labels=category_totals.index, autopct="%1.1f%%")
    plt.title("Spending Share by Category")
    plt.savefig(CHART_FOLDER + "/pie.png")
    plt.close()

    # Chart 2: Bar chart (Seaborn)
    plt.figure(figsize=(8, 5))
    sns.barplot(x=category_totals.index, y=category_totals.values, color="#4f7cff")
    plt.title("Total Spent per Category")
    plt.xlabel("Category")
    plt.ylabel("Amount (₹)")
    plt.tight_layout()
    plt.savefig(CHART_FOLDER + "/bar.png")
    plt.close()

    # Chart 3: Line chart (Matplotlib)
    plt.figure(figsize=(8, 5))
    plt.plot(monthly_totals.index, monthly_totals.values, marker="o")
    plt.title("Monthly Spending")
    plt.xlabel("Month")
    plt.ylabel("Amount (₹)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(CHART_FOLDER + "/line.png")
    plt.close()

    # Chart 4: Histogram (Seaborn)
    plt.figure(figsize=(8, 5))
    sns.histplot(df["amount"], bins=10, kde=True)
    plt.title("How Big Are My Expenses?")
    plt.xlabel("Amount (₹)")
    plt.tight_layout()
    plt.savefig(CHART_FOLDER + "/hist.png")
    plt.close()

    # Chart 5: Box plot (Seaborn)
    plt.figure(figsize=(8, 5))
    sns.boxplot(data=df, x="category", y="amount")
    plt.title("Expense Range per Category")
    plt.tight_layout()
    plt.savefig(CHART_FOLDER + "/box.png")
    plt.close()

    category_table = category_totals.reset_index().to_dict(orient="records")
    monthly_table = monthly_totals.reset_index().to_dict(orient="records")
    version = datetime.now().timestamp()  # stops the browser showing old cached charts


    return render_template("dashboard.html", stats=stats, top_category=top_category,
                           category_table=category_table, monthly_table=monthly_table,
                           version=version)


# ---------------- IMPORT CSV ----------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files["file"]

        if file.filename == "" or not file.filename.endswith(".csv"):
            flash("Please choose a .csv file.")
            return redirect(url_for("upload"))

        new_data = pd.read_csv(file)

        if list(new_data.columns) != COLUMNS:
            flash("CSV must have exactly these columns: date, category, amount, description")
            return redirect(url_for("upload"))

        new_data = new_data.dropna(subset=["date", "amount"])
        new_data["description"] = new_data["description"].fillna("-")

        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, new_data], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        flash(f"Imported {len(new_data)} expenses!")
        return redirect(url_for("view_expenses"))

    return render_template("upload.html")


# ---------------- DOWNLOAD CSV ----------------
@app.route("/download")
def download():
    return send_file(DATA_FILE, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)