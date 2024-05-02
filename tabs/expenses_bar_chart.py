import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
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

    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Expenses Bar Chart")

    # Build data matrix.
    #
    # The goal is a 2D array with one column per time period, e.g. month, and one
    # row per expense category.
    category_labels = []  # The name of each category.
    category_data = []  # One sub-list per category, each with one value per bar.

    oldest_date = transactions["date"].min()
    newest_date = transactions["date"].max()
    print("By category:")
    print(by_category)
    print("Oldest date:")
    print(oldest_date)
    print("Newest date:")
    print(newest_date)

    for category, transactions in by_category:
        transactions_resampled = (
            transactions[["date", "amount"]].set_index("date").resample("M").sum()
        )

        full_date_range = pd.date_range(start=oldest_date, end=newest_date, freq="M")
        transactions_date_expanded = transactions_resampled.reindex(
            full_date_range, fill_value=0.0
        )
        category_labels.append(category)
        category_data.append(transactions_date_expanded)

    for i, label in enumerate(category_labels):
        print(f"Category '{label}':")
        print(type(category_data[i]))
        print(category_data[i])

    # Plot the expenses as a bar chart, grouped by month.
    balance_fig, balance_ax = plt.subplots(figsize=(8, 4))


class ExpensesBarChartTab(tab.Tab):
    """Class implementing the Tab interface, populating itself with a bar chart."""

    def init(self, notebook, transactions, by_account, by_category, resample_rule):
        init_tab(notebook, transactions, by_category)


def get_tab():
    return ExpensesBarChartTab()
