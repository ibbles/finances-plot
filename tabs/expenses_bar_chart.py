import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import pandas as pd

import mplcursors
import datetime

import tab


def use_mplcursors():

    # Sample data
    categories = ["2024 January", "2024 February", "2024 March"]
    groceries = [1, 2, 3]
    electronics = [0, 5, 5]
    clothes = [0, 0, 3]
    entertainment = [1, 1, 2]
    fees = [1, 1, 2]

    expenses = [groceries, electronics, clothes, entertainment, fees]
    expenses_labels = ["Groceries", "Electronics", "Clothes", "Entertainment", "Fees"]

    tooltips = ["Tooltip 1", "Tooltip 2", "Tooltip 3"]

    # Where the place the bottom of the next bar.
    bottom = [0] * len(categories)

    # Create stacked bar chart, moving bottom up for each one.
    plt.bar(categories, groceries, label="Groceries", bottom=bottom)
    bottom = [bottom[i] + groceries[i] for i in range(len(categories))]

    plt.bar(categories, electronics, label="Electronics", bottom=bottom)
    bottom = [bottom[i] + electronics[i] for i in range(len(categories))]

    plt.bar(categories, clothes, label="Clothes", bottom=bottom)
    bottom = [bottom[i] + clothes[i] for i in range(len(clothes))]

    plt.bar(categories, entertainment, label="Entertainment", bottom=bottom)
    bottom = [bottom[i] + entertainment[i] for i in range(len(entertainment))]

    plt.bar(categories, fees, label="Fees", bottom=bottom)
    bottom = [bottom[i] + fees[i] for i in range(len(fees))]

    # Add legend
    plt.legend()

    plt.title("Stacked Bar Chart with Multiple Categories")
    plt.xlabel("Months")
    plt.ylabel("Expenses")

    cursor = mplcursors.cursor(hover=mplcursors.HoverMode.Transient)

    @cursor.connect("add")
    def on_add(sel):
        x, y, width, height = sel.artist[sel.index].get_bbox().bounds
        sel.annotation.xy = (x + width / 2, y + height)
        print(f"Hover for {x=}, {y=}, {width=}, {height=}")

        # Determine the expense type.
        sum = 0
        expense_label = ""
        for i, expense in enumerate(expenses):
            sum += expense[sel.index]
            if sum > y:
                expense_label = expenses_labels[i]
                break
        sel.annotation.set(
            # text=f"My label: {x+width/2}: {height}",
            text=expense_label,
            position=(0, 20),
            anncoords="offset points",
        )

        # expense_types = ["Groceries", "Electronics", "Clothes", "Entertainment", "Fees"]
        # for i, artist in enumerate(sel.artist):
        #     if artist == sel.artist[sel.index]:
        #         expense_type = expense_types[i]
        #         print("Expense Type:", expense_type)
        #         # print(artist.get_bbox())
        #         # print(dir(artist))
        #         break

    plt.grid(True)
    plt.show()


def init_tab(notebook, transactions, by_category):
    """Create the tab and its constituent widgets."""

    print("All transactions:")
    print(transactions)

    # This is debug code. Don't commit.
    start_date = pd.to_datetime("2024-01-01")
    end_date = pd.to_datetime("2024-12-31")
    transactions = transactions[
        (transactions["date"] >= start_date) & (transactions["date"] <= end_date)
    ]

    print("Transactions in the date range:")
    print(transactions)

    # Only keep expenses, i.e. negative amounts.
    transactions = transactions[(transactions["amount"] < 0)]
    transactions["amount"] = transactions["amount"].abs()

    print("Transactions with negative amount:")
    print(transactions)

    # Remove disabled categories.
    disabled_categories = ["Negativ avkastning"]
    for category in disabled_categories:
        transactions = transactions[(transactions["category"] != category)]

    by_category = transactions.groupby("category")

    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Expenses Bar Chart")

    if len(transactions) == 0:
        no_data_label = ttk.Label(frame, text="No data")
        no_data_label.pack()
        return

    # Build data matrix.
    #
    # The goal is a 2D array with one column per time period, e.g. month, and one
    # row per expense category.
    category_labels = []  # The name of each category.
    category_data = []  # One sub-list per category, each with one value per bar.
    category_memo = []  # One sub-list per category, each with one memo per bar.

    oldest_date = transactions["date"].min()
    oldest_date = oldest_date.replace(day=1)
    newest_date = transactions["date"].max()
    newest_date = newest_date.replace(day=1)
    newest_date = newest_date + pd.offsets.MonthBegin(1)
    full_date_range = pd.date_range(start=oldest_date, end=newest_date, freq="MS")

    print("Oldest date:")
    print(oldest_date)
    print("Newest date:")
    print(newest_date)
    print("full_date_range:")
    print(full_date_range)

    for category, transactions in by_category:
        print("Resample and date expanding")
        print(transactions)

        transactions_resampled = (
            transactions[["date", "amount"]].set_index("date").resample("MS").sum()
        )
        # transactions_memo_resampled = (
        #     transactions[["date", "memo"]].set_index("date").resample("MS").sum()
        # )
        transactions_memo_resampled = (
            transactions.groupby(pd.Grouper(key="date", freq="MS")).agg(
                {"memo": lambda x: "\n".join(x.array).strip()}
            )  # "\n".join(x) if type(x) == str else ""
            # .reset_index()
        )

        print("Resampled:")
        print(transactions_resampled)
        print(transactions_memo_resampled)

        transactions_date_expanded = transactions_resampled.reindex(
            full_date_range, fill_value=0.0
        )

        transactions_memo_date_expanded = transactions_memo_resampled.reindex(
            full_date_range, fill_value=""
        )

        print(f"Date expanded to {full_date_range}:")
        print(transactions_date_expanded)
        print(transactions_memo_date_expanded)

        category_labels.append(category)
        category_data.append(transactions_date_expanded)
        category_memo.append(transactions_memo_date_expanded)

    print("Categories:")
    for i, label in enumerate(category_labels):
        print(f"  - Category '{label}':")
        print(category_data[i])
        print(category_memo[i])
    print("End of categories.")

    # Plot the expenses as a bar chart, grouped by month.
    figure, axes = plt.subplots(figsize=(8, 4))

    width = [
        (full_date_range[i + 1] - full_date_range[i]).days
        for i in range(len(full_date_range) - 1)
    ]
    width.append(width[-1])  # Add the width for the last month
    bottom = [0] * len(full_date_range)

    # experiment_dates = ["2024-01-31", "2024-02-28", "2024-03-31"]
    # experiment_data = [10, 20, 15]
    # experiment_label = "Experiment data"
    # axes.bar(experiment_dates, experiment_data, label=experiment_label)

    for label, data in zip(category_labels, category_data):
        axes.bar(
            full_date_range,
            data["amount"],
            label=label,
            width=width,
            align="edge",
            bottom=bottom,
        )

        bottom = [
            bottom[i] + data["amount"].iloc[i] for i in range(len(full_date_range))
        ]

    axes.set_xlabel("Date")
    axes.set_ylabel("Amount")
    axes.set_title("Cost Per Month")
    axes.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
    axes.xaxis.set_major_locator(MonthLocator())
    axes.tick_params(axis="x", rotation=45)
    axes.grid(True)
    axes.legend(loc=(1.04, 0))

    canvas = FigureCanvasTkAgg(figure, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

    cursor = mplcursors.cursor(hover=mplcursors.HoverMode.Transient)

    @cursor.connect("add")
    def on_add(sel):
        x, y, width, height = sel.artist[sel.index].get_bbox().bounds
        sel.annotation.xy = (x + width / 2, y + height)

        # Determine the expense type.
        sum = 0
        expense_label = ""
        for i, expense in enumerate(category_data):
            sum += expense["amount"].iloc[sel.index]
            if sum > y:
                memo = category_memo[i]["memo"].iloc[sel.index]
                expense_label = f"{category_labels[i]}: {height:.2f}\n{memo}"
                break
        sel.annotation.set(
            text=expense_label,
            position=(0, 20),
            anncoords="offset points",
        )

        print(f"Hover over {x=}, {y=}, {width=}, {height=}, {expense_label=}")

    # TODO Add a settings panel with a checkbox for each expense category.


class ExpensesBarChartTab(tab.Tab):
    """Class implementing the Tab interface, populating itself with a bar chart."""

    def init(self, notebook, transactions, by_account, by_category, resample_rule):
        print("ExpensesBarChartTab.init")
        init_tab(notebook, transactions, by_category)


def get_tab():
    return ExpensesBarChartTab()
