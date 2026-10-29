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

os.makedirs("data", exist_ok=True)
os.makedirs(CHART_FOLDER, exist_ok=True)

if not os.path.exists(DATA_FILE):
  df=pd.DataFrame(columns=COLUMNS)
  df.to_csv(DATA_FILE, index=False )


  # when user enter our page display the sum of amt, number of transaction and last 5 transactions

  @app.route("/")
  def home():
    df = pd.read_csv(DATA_FILE)
    sum= df["amount"].sum()
    count= df.shape[0]
    last_transactions= df.tail(5).iloc[::-1].to_dict(orient="records") #[{},{}]
    return render_template("index.html",sum=sum,count=count,last_transactions=last_transactions)



# add expense get req-> show form 
#post req-> save expense to csv and redirect to view page

@app.route("/add", methods=["GET", "POST"])
def add_expense():
  if request.method == "POST":
    #  ["date", "category", "amount", "description"]
    date=request.form["date"]
    category=request.form["category"]
    amount=request.form["amount"]
    description=request.form["description"]

    if date =="" or category=="" or amount=="":
      flash("Please fill all the fields!")
      return redirect(url_for("add_expense"))
    if description == "":
      description=""

    df=pd.read_csv(DATA_FILE)
    df.loc[len(df)] = [date, category, amount, description]
    df.to_csv(DATA_FILE, index=False)
    flash("Expense added successfully!")
    return redirect(url_for("view_expenses"))

  return render_template("add.html", categories=CATEGORIES)


@app.route("/view")
#user can select a particular category or just get all expenses
def view_expenses():
  df=pd.read_csv(DATA_FILE)
  category=request.args.get("category", "all")
  if category != "all":
    df=df[df["category"]== category]  ## show me that row true true false ...
  df=df.sort_values("date", ascending=False)
  total_amount =df["amount"].sum()
  expenses = df.to_dict(orient="records")
  return render_template("expenses.html", expenses=expenses, total_amount=total_amount, category=CATEGORIES, selected_category=category)







