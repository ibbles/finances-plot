import dateutil

import tkinter as tk
from tkinter import ttk
import dateutil.rrule
from tkcalendar import DateEntry

import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter, WeekdayLocator, YearLocator
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import pandas as pd

import mplcursors
import datetime

import tab

# See https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
# SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame.
pd.options.mode.copy_on_write = True


def filter_to_date_range(
    transactions: pd.DataFrame, first_date: pd.Timestamp, last_date: pd.Timestamp
):
    """Get transactions within a data range.

    Create a new Data Frame that only contains the transactions that happened
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
    transactions.loc[:, "amount"] = transactions.loc[:, "amount"].abs()
    return transactions


def filter_away_unwanted_categories(transactions: pd.DataFrame, unwanted_categories):
    """Get transactions that are not part of any of the unwanted categories."""
    for category in unwanted_categories:
        transactions = transactions[(transactions["category"] != category)]
    return transactions


def filter_away_large_expenses(transactions: pd.DataFrame, amount_threshold):
    """Get transactions that are not too large."""
    transactions = transactions[(transactions["amount"] < amount_threshold)]
    return transactions


def create_settings(frame: ttk.Frame, apply_callback):
    # Settings panel for date range selection
    settings_frame = ttk.Frame(frame)
    settings_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

    today = datetime.date.today()
    year = today.year

    ttk.Label(settings_frame, text="Start Date:").grid(row=0, column=0, padx=5, pady=5)
    start_date_entry = DateEntry(
        settings_frame,
        width=12,
        year=year,
        month=1,
        day=1,
        background="darkblue",
        foreground="white",
        borderwidth=2,
    )
    start_date_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(settings_frame, text="End Date:").grid(row=0, column=2, padx=5, pady=5)
    end_date_entry = DateEntry(
        settings_frame,
        width=12,
        year=year,
        month=12,
        day=31,
        background="darkblue",
        foreground="white",
        borderwidth=2,
    )
    end_date_entry.grid(row=0, column=3, padx=5, pady=5)

    # Add dropdown for resampling frequency
    ttk.Label(settings_frame, text="Resample By:").grid(row=0, column=4, padx=5, pady=5)
    resample_option = ttk.Combobox(
        settings_frame, values=["W", "MS", "YS"], state="readonly"
    )
    resample_option.current(1)  # Default to "M" (monthly)
    resample_option.grid(row=0, column=5, padx=5, pady=5)

    ttk.Label(settings_frame, text="Max amount:").grid(row=0, column=6, padx=5, pady=5)
    amount_threshold_entry = ttk.Spinbox(
        settings_frame, from_=0, to=100000, increment=1000
    )
    amount_threshold_entry.set(0)
    amount_threshold_entry.grid(row=0, column=7, padx=5, pady=5)

    apply_button = ttk.Button(settings_frame, text="Apply", command=apply_callback)
    apply_button.grid(row=0, column=8, padx=5, pady=5)

    return start_date_entry, end_date_entry, resample_option, amount_threshold_entry


def init_tab(notebook, transactions: pd.DataFrame, by_category):
    """Create the tab and its constituent widgets."""

    # Create main GUI container widget.
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Expenses Bar Chart")

    def apply_date_filter():
        start_date = pd.to_datetime(start_date_entry.get())
        end_date = pd.to_datetime(end_date_entry.get())
        resample_rule = resample_option.get()
        try:
            amount_threshold = int(amount_threshold_entry.get())
        except ValueError:
            amount_threshold = None
        update_plot(start_date, end_date, resample_rule, amount_threshold)

    start_date_entry, end_date_entry, resample_option, amount_threshold_entry = (
        create_settings(frame, apply_date_filter)
    )

    # Keep a copy of the transactions list so that we can re-run the filtering
    # with different settings later.
    original_transactions = transactions.copy()

    # Placeholder for canvas and no_data_label.
    plot_frame = ttk.Frame(frame)
    plot_frame.pack(expand=True, fill=tk.BOTH)
    plot_canvas = None
    no_data_label = None

    # Function to update the plot with the selected date range
    def update_plot(start_date, end_date, resample_rule, amount_threshold):
        nonlocal plot_canvas, no_data_label

        if amount_threshold == 0:
            amount_threshold = None

        # Clear previous plot or message.
        if plot_canvas is not None:
            plot_canvas.get_tk_widget().destroy()
            plot_canvas = None

        if no_data_label is not None:
            no_data_label.destroy()
            no_data_label = None

        # Only include transactions in the selected date range.
        filtered_transactions = filter_to_date_range(
            original_transactions, start_date, end_date
        )

        # Only include expenses.
        filtered_transactions = filter_to_expenses(filtered_transactions)

        # Remove transactions in categories that aren't "real" expenses.
        unwanted_categories = [
            "Negativ avkastning"  # Value changes in investments is not an expense.
        ]
        filtered_transactions = filter_away_unwanted_categories(
            filtered_transactions, unwanted_categories
        )

        if amount_threshold is not None:
            filtered_transactions = filter_away_large_expenses(
                filtered_transactions, amount_threshold
            )

        # Sort categories by the total amount spent in each category, descending.
        sorted_categories = (
            filtered_transactions.groupby("category")["amount"]
            .sum()
            .sort_values(ascending=False)
            .index
        )
        filtered_transactions["category"] = pd.Categorical(
            filtered_transactions["category"],
            categories=sorted_categories,
            ordered=True,
        )
        by_category = filtered_transactions.groupby("category", observed=False)

        # Bail if there is no data to plot.
        if len(filtered_transactions) == 0:
            no_data_label = ttk.Label(plot_frame, text="No data")
            no_data_label.pack()
            return

        # Build plot data matrix.
        category_labels = []  # The name of each category.
        category_data = []  # One sub-list per category, each with one value per bar.
        category_memo = []  # One sub-list per category, each with one memo per bar.

        # Find the actual date range of the final data set. Round the oldest_date
        # down to the start of the month and newest_date up to the next month to
        # make sure we only have complete months.
        oldest_date = filtered_transactions["date"].min()
        newest_date = filtered_transactions["date"].max()
        if resample_rule == "W" or resample_rule == "W-MON":
            oldest_date -= pd.to_timedelta(oldest_date.dayofweek, unit="d")
            newest_date += pd.to_timedelta(7 - newest_date.dayofweek, unit="d")
        elif resample_rule == "MS":
            oldest_date = oldest_date.replace(day=1)
            newest_date += pd.offsets.MonthBegin(1)
        elif resample_rule == "YS":
            oldest_date = oldest_date.replace(month=1).replace(day=1)
            newest_date += pd.offsets.YearBegin(1)
        full_date_range = pd.date_range(
            start=oldest_date, end=newest_date, freq=resample_rule
        )

        # Populate the plot data for each category.
        for category, transactions in by_category:
            transactions_resampled = (
                transactions[["date", "amount"]]
                .set_index("date")
                .resample(resample_rule)
                .sum()
            )
            transactions_date_expanded = transactions_resampled.reindex(
                full_date_range, fill_value=0.0
            )

            transactions_memo_resampled = transactions.groupby(
                pd.Grouper(key="date", freq=resample_rule)
            ).agg(
                {
                    "memo": lambda x: "\n".join(
                        f"{memo}: {amt:.2f}"
                        for memo, amt in zip(x, transactions.loc[x.index, "amount"])
                        if memo != ""
                    )
                }
            )
            transactions_memo_date_expanded = transactions_memo_resampled.reindex(
                full_date_range, fill_value=""
            )

            category_labels.append(category)
            category_data.append(transactions_date_expanded)
            category_memo.append(transactions_memo_date_expanded)

        # Create a figure to draw the bar chart in.
        figure, axes = plt.subplots(figsize=(8, 4))

        width = [
            (full_date_range[i + 1] - full_date_range[i]).days
            for i in range(len(full_date_range) - 1)
        ]
        # Add the width for the last period. Don't know how long it actually is
        # so use the second-to-last width again. Doesn't matter much since there
        # is no neighbor on the right side.
        width.append(width[-1])

        bottom = [0] * len(full_date_range)

        # Build the bar chart one category at a time, starting from the largest.
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

        # Configure the plot based on resampling rule.
        axes.set_xlabel("Date")
        axes.set_ylabel("Amount")

        if resample_rule == "W" or resample_rule == "W-MON":
            axes.set_title("Cost Per Week")
            axes.xaxis.set_major_formatter(DateFormatter("%Y W%W"))
            axes.xaxis.set_major_locator(WeekdayLocator(dateutil.rrule.SU))
        elif resample_rule == "MS":
            axes.set_title("Cost Per Month")
            axes.xaxis.set_major_formatter(DateFormatter("%Y-%m"))
            axes.xaxis.set_major_locator(MonthLocator())
        elif resample_rule == "YS":
            axes.set_title("Cost Per Year")
            axes.xaxis.set_major_formatter(DateFormatter("%Y"))
            axes.xaxis.set_major_locator(YearLocator())

        axes.tick_params(axis="x", rotation=45)
        axes.grid(True)
        axes.legend(loc=(1.04, 0))

        # Present the finished plot to the user.
        plot_canvas = FigureCanvasTkAgg(figure, master=plot_frame)
        plot_canvas.draw()
        plot_canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        # Set up the category hover tool-tips.
        cursor = mplcursors.cursor(figure, hover=mplcursors.HoverMode.Transient)

        @cursor.connect("add")
        def on_add(sel):
            """Callback called by mplcursors when the mouse cursor is moved over the bar chart."""

            # Find which part of the bar chart the cursor is currently on top of.
            x, y, width, height = sel.artist[sel.index].get_bbox().bounds
            sel.annotation.xy = (x + width / 2, y + height)

            # Determine the expense type by walking up the categories in the current
            # column until we have seen enough amounts to enter into the current
            # bar chart box, i.e. until the sum of expenses is larger than the y
            # coordinate of the box.
            total = 0
            expense_label = ""
            for i, expense in enumerate(category_data):
                total += expense["amount"].iloc[sel.index]
                if total > y:
                    memo = category_memo[i]["memo"].iloc[sel.index]
                    expense_label = f"{category_labels[i]}: {height:.2f}\n{memo}"
                    break

            # Assign the tool-tip text.
            sel.annotation.set(
                text=expense_label,
                position=(0, 20),
                anncoords="offset points",
            )

    # Initialize plot with default date range
    start_date = pd.to_datetime(start_date_entry.get())
    end_date = pd.to_datetime(end_date_entry.get())
    resample_rule = resample_option.get()
    try:
        amount_threshold = int(amount_threshold_entry.get())
    except ValueError:
        amount_threshold = None
    update_plot(start_date, end_date, resample_rule, amount_threshold)


class ExpensesBarChartTab(tab.Tab):
    """Class implementing the Tab interface, populating itself with a bar chart."""

    def init(
        self, notebook, transactions, by_account, by_category, resample_rule, verbose
    ):
        print("ExpensesBarChartTab.init")
        init_tab(notebook, transactions, by_category)


def get_tab():
    return ExpensesBarChartTab()
