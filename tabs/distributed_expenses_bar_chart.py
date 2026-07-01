"""Distributed Expenses Bar Chart is a tab that displays expenses as a bar per
week, month, or year. Each bar consists of the expense categories as stacked
boxes. For large expences, instead of having each such expense contribute its
whole amount to the week/month/year where it was recorded, this tab distributes
the cost over multiple months. The purpose is to give a more representative
view of the per-peried expenses, to smooth out time periods with high-expense
transactions and let low-expense time periods take some of the load.
Additionally, it gives a pay-it-off view of large expenses in that the user is
encourage to remember large prior expenses and avoid taking on new expenses
until the previous one has been "paied off"."""


# UI imports.
import tkinter as tk
from tkinter import ttk
import dateutil.rrule
from tkcalendar import DateEntry

# Plotting imports.
import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter, WeekdayLocator, YearLocator
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import mplcursors

# Data processing imports.
import pandas as pd

# Standard library imports.
import datetime
import dateutil
import threading

# Project imports.
import tab

# See https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
# SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame.
pd.options.mode.copy_on_write = True

# The amount above which a transaction is to be split into chunks.
default_threshold = 5000

# For transactions larger than the threshold, the chunk size it should be split into.
default_chunksize = 5000


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

    The amounts are made positive in the returned DataFrame for easier plotting.
    """
    transactions = transactions[(transactions["amount"] < 0)]
    transactions.loc[:, "amount"] = transactions.loc[:, "amount"].abs()
    return transactions


def filter_away_unwanted_categories(transactions: pd.DataFrame, unwanted_categories):
    """Get transactions that are not part of any of the unwanted categories."""
    for category in unwanted_categories:
        transactions = transactions[(transactions["category"] != category)]
    return transactions


def filter_away_large_expenses(transactions: pd.DataFrame, threshold_value):
    """Get transactions that are not too large."""
    transactions = transactions[(transactions["amount"] < threshold_value)]
    return transactions


def split_large_expenses(
    transactions: pd.DataFrame, threshold: float, chunk_size: float
):
    """Split large expenses into smaller chunks and distribute them over neighboring months.

    Parameters:
        transactions: pd.DataFrame - DataFrame containing transactions.
        threshold: float - Amount above which transactions will be split.
        chunk_size: float - Size of each chunk.

    Returns:
        pd.DataFrame - Modified DataFrame with large expenses split into smaller chunks.
    """
    new_transactions = []

    for _, transaction in transactions.iterrows():
        if transaction["amount"] > threshold:
            num_chunks = int(transaction["amount"] // chunk_size)
            remainder = transaction["amount"] % chunk_size
            total_chunks = num_chunks + (1 if remainder > 0 else 0)

            # Split the transaction into chunks
            current_date = transaction["date"]
            for i in range(total_chunks):
                chunk_amount = chunk_size if i < num_chunks else remainder
                chunk_memo = f"{transaction['memo']} ({i + 1}/{total_chunks})"
                new_transactions.append(
                    {
                        "date": current_date,
                        "amount": chunk_amount,
                        "category": transaction["category"],
                        "memo": chunk_memo,
                    }
                )
                # Move to the next month for each chunk
                current_date += pd.offsets.MonthBegin(1)
        else:
            new_transactions.append(transaction.to_dict())

    return pd.DataFrame(new_transactions)


def prepare_transactions_for_plot(
    transactions: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    threshold_value,
    chunk_size,
    verbose: bool = False,
):
    """Filter and split transactions into the rows that should be plotted."""

    # Only include expenses.
    filtered_transactions = filter_to_expenses(transactions)

    # Remove transactions in categories that aren't "real" expenses.
    # TODO Should we provide the option to filter away accounts as well?
    unwanted_categories = [
        "Negativ avkastning"  # Value changes in investments is not an expense.
    ]
    filtered_transactions = filter_away_unwanted_categories(
        filtered_transactions, unwanted_categories
    )

    if verbose:
        print(f"After expense/category filtering: {len(filtered_transactions)}")

    # Split large expenses before date filtering so chunks from earlier
    # transactions can contribute inside the selected date range.
    if threshold_value is not None and chunk_size is not None:
        filtered_transactions = split_large_expenses(
            filtered_transactions, threshold_value, chunk_size
        )

    if verbose:
        print(f"After chunking: {len(filtered_transactions)}")

    # Only display chunks and transactions in the selected date range.
    filtered_transactions = filter_to_date_range(
        filtered_transactions, start_date, end_date
    )

    if verbose:
        print(f"After date filtering: {len(filtered_transactions)}")

    return filtered_transactions


def add_tooltip(widget, text):
    tooltip_window = None
    tooltip_after_id = None

    def show_tooltip():
        nonlocal tooltip_window, tooltip_after_id
        tooltip_after_id = None
        if tooltip_window is not None:
            return

        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 5
        tooltip_window = tk.Toplevel(widget)
        tooltip_window.wm_overrideredirect(True)
        tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tooltip_window,
            text=text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            padx=5,
            pady=3,
        )
        label.pack()

    def hide_tooltip():
        nonlocal tooltip_window, tooltip_after_id
        if tooltip_after_id is not None:
            widget.after_cancel(tooltip_after_id)
            tooltip_after_id = None
        if tooltip_window is not None:
            tooltip_window.destroy()
            tooltip_window = None

    def schedule_tooltip(_event):
        nonlocal tooltip_after_id
        if tooltip_after_id is None:
            tooltip_after_id = widget.after(500, show_tooltip)

    widget.bind("<Enter>", schedule_tooltip, add="+")
    widget.bind("<Leave>", lambda _event: hide_tooltip(), add="+")
    widget.bind("<ButtonPress>", lambda _event: hide_tooltip(), add="+")


def create_settings_panel(frame: ttk.Frame, apply_callback):
    # Settings panel for date range selection
    settings_frame = ttk.Frame(frame)
    settings_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

    today = datetime.date.today()
    year = today.year

    column = 0
    row = 0
    common_grid_options = {"padx": 5, "pady": 5, "sticky": "w"}

    ttk.Label(settings_frame, text="Start Date:").grid(
        row=row, column=column, **common_grid_options
    )
    column += 1
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
    start_date_entry.grid(row=row, column=column, **common_grid_options)
    column += 1

    ttk.Label(settings_frame, text="End Date:").grid(
        row=row, column=column, **common_grid_options
    )
    column += 1
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
    end_date_entry.grid(row=row, column=column, **common_grid_options)
    column += 1

    ttk.Label(settings_frame, text="Cut-off Date:").grid(
        row=row, column=column, **common_grid_options
    )
    column += 1
    cutoff_date_entry = DateEntry(
        settings_frame,
        width=12,
        year=year + 1,
        month=12,
        day=31,
        background="darkblue",
        foreground="white",
        borderwidth=2,
    )
    cutoff_date_entry.grid(row=row, column=column, **common_grid_options)
    column += 1

    row += 1
    column = 0

    # Add dropdown for resampling frequency
    ttk.Label(settings_frame, text="Resample By:").grid(
        row=row, column=column, **common_grid_options
    )
    column += 1
    resample_option = ttk.Combobox(
        settings_frame, values=["W", "MS", "YS"], state="readonly"
    )
    resample_option.current(1)  # Default to "M" (monthly)
    resample_option.grid(row=row, column=column, **common_grid_options)
    column += 1

    threshold_label = ttk.Label(settings_frame, text="Chunking Threshold:")
    threshold_label.grid(row=row, column=column, **common_grid_options)
    add_tooltip(
        threshold_label,
        "Expenses above this amount are split into chunks and distributed over "
        "future months. Set to 0 to disable chunking.",
    )
    column += 1
    threshold_entry = ttk.Spinbox(
        settings_frame, from_=0, to=100000, increment=1000
    )
    threshold_entry.set(default_threshold)
    threshold_entry.grid(row=row, column=column, **common_grid_options)
    column += 1

    ttk.Label(settings_frame, text="Chunk size:").grid(
        row=row, column=column, **common_grid_options
    )
    column += 1
    chunk_size_entry = ttk.Spinbox(settings_frame, from_=100, to=10000, increment=100)
    chunk_size_entry.set(default_chunksize)
    chunk_size_entry.grid(row=row, column=column, **common_grid_options)
    column += 1

    row += 1
    column = 0

    apply_button = ttk.Button(settings_frame, text="Apply", command=apply_callback)
    apply_button.grid(row=row, column=column, **common_grid_options)
    column += 1

    return (
        start_date_entry,
        end_date_entry,
        cutoff_date_entry,
        resample_option,
        threshold_entry,
        chunk_size_entry,
    )


def init_tab(notebook, transactions: pd.DataFrame, by_category, verbose):
    """Create the tab and its constituent widgets."""

    # Create main GUI container widget.
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Distributed Expenses Bar Chart")

    def apply_date_filter():
        start_date = pd.to_datetime(start_date_entry.get())
        end_date = pd.to_datetime(end_date_entry.get())
        cutoff_date = pd.to_datetime(cutoff_date_entry.get())
        resample_rule = resample_option.get()
        try:
            threshold_value = int(threshold_entry.get())
        except ValueError:
            threshold_value = None
        try:
            chunk_size = int(chunk_size_entry.get())
        except ValueError:
            chunk_size = None
        update_plot(
            start_date,
            end_date,
            cutoff_date,
            resample_rule,
            threshold_value,
            chunk_size,
        )

    (
        start_date_entry,
        end_date_entry,
        cutoff_date_entry,
        resample_option,
        threshold_entry,
        chunk_size_entry,
    ) = create_settings_panel(frame, apply_date_filter)

    # Keep a copy of the transactions list so that we can re-run the filtering
    # with different settings later.
    original_transactions = transactions.copy()

    # Placeholder for canvas and no_data_label.
    plot_frame = ttk.Frame(frame)
    plot_frame.pack(expand=True, fill=tk.BOTH)
    plot_canvas = None
    no_data_label = None

    # Function to update the plot with the selected date range.
    def update_plot(
        start_date, end_date, cutoff_date, resample_rule, threshold_value, chunk_size
    ):
        nonlocal plot_canvas, no_data_label

        if threshold_value == 0:
            threshold_value = None

        # Clear previous plot or message.
        if plot_canvas is not None:
            plot_canvas.get_tk_widget().destroy()
            plot_canvas = None

        if no_data_label is not None:
            no_data_label.destroy()
            no_data_label = None

        filtered_transactions = prepare_transactions_for_plot(
            original_transactions,
            start_date,
            end_date,
            threshold_value,
            chunk_size,
            verbose,
        )

        # Bail if there is no data to plot.
        if len(filtered_transactions) == 0:
            no_data_label = ttk.Label(plot_frame, text="No data")
            no_data_label.pack()
            return

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
        newest_date = min(newest_date, cutoff_date)
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

        def create_tooltip_text(sel):
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

            return expense_label

        tooltip_timer = None
        last_selection = None
        tooltip_text = ""

        def update_tooltip():
            nonlocal last_selection
            nonlocal tooltip_text
            nonlocal tooltip_timer
            tooltip_timer = None
            tooltip_text = create_tooltip_text(last_selection)
            # Assign the tool-tip text.
            last_selection.annotation.set(
                text=tooltip_text,
                position=(0, 20),
                anncoords="offset points",
            )
            plot_canvas.draw_idle()

        # def update_last_mouse_position(position):
        #     print("Got new mouse position")

        # plot_canvas.mpl_connect(
        #     "motion_notify_event",
        #     lambda event: update_last_mouse_position((event.x, event.y)),
        # )

        # Set up the category hover tool-tips.
        cursor = mplcursors.cursor(figure, hover=mplcursors.HoverMode.Transient)

        @cursor.connect("add")
        def on_add(selection):
            """Callback called by mplcursors when the mouse cursor is moved over the bar chart."""
            nonlocal last_selection
            nonlocal tooltip_timer
            nonlocal tooltip_text
            if tooltip_timer is not None:
                tooltip_timer.cancel()

            if last_selection is not selection:
                last_selection = selection
                tooltip_timer = threading.Timer(0.5, update_tooltip)
                tooltip_timer.start()

            tooltip_text = ""
            selection.annotation.set(
                text=tooltip_text, position=(0, 20), anncoords="offset points"
            )

    # Initialize plot with default date range
    start_date = pd.to_datetime(start_date_entry.get())
    end_date = pd.to_datetime(end_date_entry.get())
    cutoff_date = pd.to_datetime(cutoff_date_entry.get())
    resample_rule = resample_option.get()
    try:
        threshold_value = int(threshold_entry.get())
    except ValueError:
        threshold_value = None
    try:
        chunk_size = int(chunk_size_entry.get())
    except ValueError:
        chunk_size = None
    update_plot(
        start_date, end_date, cutoff_date, resample_rule, threshold_value, chunk_size
    )


class DistributedExpensesBarChartTab(tab.Tab):
    """Class implementing the Tab interface, populating itself with a bar chart."""

    def init(
        self, notebook, transactions, by_account, by_category, resample_rule, verbose
    ):
        print("DistributedExpensesBarChartTab.init")
        init_tab(notebook, transactions, by_category, verbose)


def get_tab():
    return DistributedExpensesBarChartTab()
