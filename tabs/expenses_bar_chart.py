import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import pandas as pd

import mplcursors
import datetime

import tab


def filter_to_date_range(
    transactions: pd.DataFrame, first_date: pd.Timestamp, last_date: pd.Timestamp
):
    """Get transactions within a data range.

    Crate a new Data Frame that only contains the transactions that happened
    within the requested time span. The time span is inclusive, meaning that
    both the first and last dates are included.
    """
    transactions = transactions[
        (transactions["date"] >= first_date) & (transactions["date"] <= last_date)
    ]
    return transactions


def filter_to_expenses(transactions: pd.DataFrame):
    """Get transactions that are expenses, i.e. have a negative amount.

    The amounts are made positive.
    """
    transactions = transactions[(transactions["amount"] < 0)]
    transactions["amount"] = transactions["amount"].abs()
    return transactions


def filter_away_unwanted_categories(transactions: pd.DataFrame, unwanted_categories):
    """Get transactions that are not part of any of the unwanted categories."""
    for category in unwanted_categories:
        transactions = transactions[(transactions["category"] != category)]
    return transactions


def init_tab(notebook, transactions: pd.DataFrame, by_category):
    """Create the tab and its constituent widgets."""

    # Create main GUI container widget.
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Expenses Bar Chart")

    # Only include transactions in the wanted date range, inclusive on both ends.
    start_date = pd.to_datetime("2023-01-01")
    end_date = pd.to_datetime("2023-12-31")
    transactions = filter_to_date_range(transactions, start_date, end_date)

    # Only keep expenses, i.e. transactions that have negative amounts.
    transactions = filter_to_expenses(transactions)

    # Remove unwanted categories.
    # "Negative avkastning" is unwanted because it is not an expense.
    unwanted_categories = ["Negativ avkastning"]
    transactions = filter_away_unwanted_categories(transactions, unwanted_categories)

    by_category = transactions.groupby("category")

    # Bail if there is no data to plot.
    if len(transactions) == 0:
        no_data_label = ttk.Label(frame, text="No data")
        no_data_label.pack()
        return

    # Build plot data matrix.
    #
    # The goal is a 2D array with one column per time period, e.g. month, and
    # one row per expense category. Each column corresponds to a bar in the bar
    # chart.
    category_labels = []  # The name of each category.
    category_data = []  # One sub-list per category, each with one value per bar.
    category_memo = []  # One sub-list per category, each with one memo per bar.

    # Find the actual date range of the final data set. Round the oldest_date
    # down to the start of the month and newest_date up to the next month to
    # make sure we only have complete months.
    oldest_date = transactions["date"].min()
    oldest_date = oldest_date.replace(day=1)
    newest_date = transactions["date"].max()
    newest_date = newest_date.replace(day=1)
    newest_date = newest_date + pd.offsets.MonthBegin(1)
    full_date_range = pd.date_range(start=oldest_date, end=newest_date, freq="MS")

    # Populate the plot data for each category.
    for category, transactions in by_category:
        # Resample transactions by month. Fill with 0.0 for months where there
        # is no data.
        transactions_resampled = (
            transactions[["date", "amount"]].set_index("date").resample("MS").sum()
        )
        transactions_date_expanded = transactions_resampled.reindex(
            full_date_range, fill_value=0.0
        )

        # Create a combined label for all memos during each month. Use the empty
        # string for months where there is no data.
        transactions_memo_resampled = transactions.groupby(
            pd.Grouper(key="date", freq="MS")
        ).agg({"memo": lambda x: "\n".join(x.array).strip()})
        transactions_memo_date_expanded = transactions_memo_resampled.reindex(
            full_date_range, fill_value=""
        )

        # Populate the plot data matrix.
        category_labels.append(category)
        category_data.append(transactions_date_expanded)
        category_memo.append(transactions_memo_date_expanded)

    # Create a figure to draw the bar chart in.
    figure, axes = plt.subplots(figsize=(8, 4))

    # Not sure what this does. Will all widths be the same, or is there some
    # variation? Does it scale the width of each bar by the number of days in
    # each month? That doesn't seem necessary.
    width = [
        (full_date_range[i + 1] - full_date_range[i]).days
        for i in range(len(full_date_range) - 1)
    ]
    width.append(width[-1])  # Add the width for the last month.
    # The last row above is weird. It adds the last width again. Why?

    print(f"width: {width}")

    # The bar chart is built one category at a time, each new category being
    # stacked on top of the prior one. This array keeps track of how high each
    # bar, i.e. each month, has stacked so far. When we add the next category
    # at the top of the bar then that category's block should start at this
    # height.
    bottom = [0] * len(full_date_range)

    # Build the bar chart one category at a time.
    for label, data in zip(category_labels, category_data):
        # Draw the bar boxes for this category across all months, placing them
        # on top of the the previous boxes, i.e. 'bottom'.
        axes.bar(
            full_date_range,
            data["amount"],
            label=label,
            width=width,
            align="edge",
            bottom=bottom,
        )

        # Move the bottom up by each months' amount for this category.
        bottom = [
            bottom[i] + data["amount"].iloc[i] for i in range(len(full_date_range))
        ]

    # Configure the plot.
    axes.set_xlabel("Date")
    axes.set_ylabel("Amount")
    axes.set_title("Cost Per Month")
    axes.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
    axes.xaxis.set_major_locator(MonthLocator())
    axes.tick_params(axis="x", rotation=45)
    axes.grid(True)
    axes.legend(loc=(1.04, 0))

    # Present the finished plot to the user.
    canvas = FigureCanvasTkAgg(figure, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

    # Set up the category hover tool-tips.
    cursor = mplcursors.cursor(hover=mplcursors.HoverMode.Transient)

    @cursor.connect("add")
    def on_add(sel):
        """Callback called by mplcursors when the mouse cursos is moved over the bar char."""

        # Find which part of the bar chart the cursor is currently on top of.
        x, y, width, height = sel.artist[sel.index].get_bbox().bounds
        sel.annotation.xy = (x + width / 2, y + height)

        # Determine the expense type by walking up the categories in the current
        # column until we have seen enough amounts to enter into the current
        # bar chart box, i.e. until the sum of expenses is larger than the y
        # coordinate of the box.
        sum = 0
        expense_label = ""
        for i, expense in enumerate(category_data):
            sum += expense["amount"].iloc[sel.index]
            if sum > y:
                # Found the box.
                memo = category_memo[i]["memo"].iloc[sel.index]
                expense_label = f"{category_labels[i]}: {height:.2f}\n{memo}"
                break

        # Assign the tool-tip text.
        sel.annotation.set(
            text=expense_label,
            position=(0, 20),
            anncoords="offset points",
        )


class ExpensesBarChartTab(tab.Tab):
    """Class implementing the Tab interface, populating itself with a bar chart."""

    def init(self, notebook, transactions, by_account, by_category, resample_rule):
        print("ExpensesBarChartTab.init")
        init_tab(notebook, transactions, by_category)


def get_tab():
    return ExpensesBarChartTab()
