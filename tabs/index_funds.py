"""A tab showing long-term index fund value split by deposits and returns."""

import datetime
import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
import pandas as pd
from tkcalendar import DateEntry

import tab


RETURN_CATEGORIES = {"Avkastning", "Negativ avkastning"}


def is_return_category(category) -> bool:
    """Return whether a transaction category represents a value sync."""
    if pd.isna(category):
        return False
    return str(category).strip() in RETURN_CATEGORIES


def get_index_fund_accounts(transactions: pd.DataFrame) -> list[str]:
    """Find accounts that have index-fund return synchronization rows."""
    return_transactions = transactions[
        transactions["category"].apply(is_return_category)
    ]
    accounts = sorted(return_transactions["account"].dropna().unique())
    if len(accounts) > 0:
        return accounts
    return sorted(transactions["account"].dropna().unique())


def create_state_row(date: pd.Timestamp, value: float, principal_basis: float) -> dict:
    """Create one row of plot state from the current accounting state."""
    deposit_value = max(min(value, principal_basis), 0.0)
    positive_returns = max(value - principal_basis, 0.0)
    principal_loss = max(principal_basis - value, 0.0)
    return {
        "date": date,
        "value": value,
        "principal_basis": principal_basis,
        "deposit_value": deposit_value,
        "positive_returns": positive_returns,
        "principal_loss": principal_loss,
    }


def prepare_index_fund_series(
    transactions: pd.DataFrame,
    account: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """Build the accounting series used by the index-funds plot."""
    columns = [
        "date",
        "value",
        "principal_basis",
        "deposit_value",
        "positive_returns",
        "principal_loss",
    ]

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    account_transactions = transactions[transactions["account"] == account].copy()
    if len(account_transactions) == 0:
        return pd.DataFrame(columns=columns)

    account_transactions["_row_order"] = range(len(account_transactions))
    account_transactions["date"] = pd.to_datetime(account_transactions["date"])
    account_transactions = account_transactions[
        account_transactions["date"] <= end_date
    ].sort_values(["date", "_row_order"])

    if len(account_transactions) == 0:
        return pd.DataFrame(columns=columns)

    value = 0.0
    principal_basis = 0.0
    state_before_start = None
    state_rows = []
    current_date = None

    for _, transaction in account_transactions.iterrows():
        transaction_date = transaction["date"]
        if current_date is not None and transaction_date != current_date:
            row = create_state_row(current_date, value, principal_basis)
            if current_date < start_date:
                state_before_start = row
            else:
                state_rows.append(row)

        amount = float(transaction["amount"])
        value += amount

        if not is_return_category(transaction["category"]):
            if amount >= 0:
                principal_basis += amount
            else:
                principal_basis = max(0.0, principal_basis + amount)

        current_date = transaction_date

    if current_date is not None:
        row = create_state_row(current_date, value, principal_basis)
        if current_date < start_date:
            state_before_start = row
        else:
            state_rows.append(row)

    if state_before_start is not None and (
        len(state_rows) == 0 or state_rows[0]["date"] > start_date
    ):
        state_rows.insert(
            0,
            create_state_row(
                start_date,
                state_before_start["value"],
                state_before_start["principal_basis"],
            ),
        )

    if len(state_rows) == 0:
        return pd.DataFrame(columns=columns)

    if state_rows[-1]["date"] < end_date:
        state_rows.append(
            create_state_row(
                end_date,
                state_rows[-1]["value"],
                state_rows[-1]["principal_basis"],
            )
        )

    return pd.DataFrame(state_rows, columns=columns)


def create_settings_panel(frame: ttk.Frame, accounts: list[str], apply_callback):
    """Create the settings widgets for the tab."""
    settings_frame = ttk.Frame(frame)
    settings_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

    today = datetime.date.today()
    common_grid_options = {"padx": 5, "pady": 5, "sticky": "w"}

    ttk.Label(settings_frame, text="Account:").grid(
        row=0, column=0, **common_grid_options
    )
    account_option = ttk.Combobox(settings_frame, values=accounts, state="readonly")
    if len(accounts) > 0:
        account_option.current(0)
    account_option.grid(row=0, column=1, **common_grid_options)

    ttk.Label(settings_frame, text="Start Date:").grid(
        row=0, column=2, **common_grid_options
    )
    start_date_entry = DateEntry(
        settings_frame,
        width=12,
        year=today.year,
        month=1,
        day=1,
        background="darkblue",
        foreground="white",
        borderwidth=2,
    )
    start_date_entry.grid(row=0, column=3, **common_grid_options)

    ttk.Label(settings_frame, text="End Date:").grid(
        row=0, column=4, **common_grid_options
    )
    end_date_entry = DateEntry(
        settings_frame,
        width=12,
        year=today.year,
        month=12,
        day=31,
        background="darkblue",
        foreground="white",
        borderwidth=2,
    )
    end_date_entry.grid(row=0, column=5, **common_grid_options)

    apply_button = ttk.Button(settings_frame, text="Apply", command=apply_callback)
    apply_button.grid(row=0, column=6, **common_grid_options)

    return account_option, start_date_entry, end_date_entry


def set_date_entry(date_entry: DateEntry, date: pd.Timestamp):
    """Set a DateEntry without depending on locale-specific string parsing."""
    date_entry.set_date(date.to_pydatetime().date())


def init_tab(notebook, transactions: pd.DataFrame):
    """Create the tab and its constituent widgets."""
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Index Funds")

    accounts = get_index_fund_accounts(transactions)
    original_transactions = transactions.copy()

    plot_frame = ttk.Frame(frame)
    plot_frame.pack(expand=True, fill=tk.BOTH)
    plot_canvas = None
    no_data_label = None

    def update_date_entries_for_account(account: str):
        account_transactions = original_transactions[
            original_transactions["account"] == account
        ]
        if len(account_transactions) == 0:
            return
        set_date_entry(start_date_entry, account_transactions["date"].min())
        set_date_entry(end_date_entry, account_transactions["date"].max())

    def apply_settings():
        update_plot(
            account_option.get(),
            pd.to_datetime(start_date_entry.get()),
            pd.to_datetime(end_date_entry.get()),
        )

    account_option, start_date_entry, end_date_entry = create_settings_panel(
        frame, accounts, apply_settings
    )
    account_option.bind(
        "<<ComboboxSelected>>",
        lambda _event: update_date_entries_for_account(account_option.get()),
        add="+",
    )

    def update_plot(account: str, start_date: pd.Timestamp, end_date: pd.Timestamp):
        nonlocal plot_canvas, no_data_label

        if plot_canvas is not None:
            plot_canvas.get_tk_widget().destroy()
            plot_canvas = None

        if no_data_label is not None:
            no_data_label.destroy()
            no_data_label = None

        plot_data = prepare_index_fund_series(
            original_transactions, account, start_date, end_date
        )

        if len(plot_data) == 0:
            no_data_label = ttk.Label(plot_frame, text="No data")
            no_data_label.pack()
            return

        figure, axes = plt.subplots(figsize=(8, 4))
        dates = plot_data["date"].dt.to_pydatetime()
        value = plot_data["value"].to_numpy()
        principal_basis = plot_data["principal_basis"].to_numpy()
        deposit_value = plot_data["deposit_value"].to_numpy()

        axes.fill_between(
            dates,
            0,
            deposit_value,
            color="#4c78a8",
            alpha=0.35,
            label="Deposits",
        )
        axes.fill_between(
            dates,
            principal_basis,
            value,
            where=value >= principal_basis,
            interpolate=True,
            color="#59a14f",
            alpha=0.35,
            label="Returns",
        )
        axes.fill_between(
            dates,
            value,
            principal_basis,
            where=value < principal_basis,
            interpolate=True,
            color="#e15759",
            alpha=0.35,
            label="Loss into deposits",
        )
        axes.plot(
            dates,
            value,
            color="#1f2933",
            linewidth=1.8,
            label="Value",
        )

        locator = AutoDateLocator()
        axes.xaxis.set_major_locator(locator)
        axes.xaxis.set_major_formatter(ConciseDateFormatter(locator))
        axes.set_xlabel("Date")
        axes.set_ylabel("Amount")
        axes.set_title(f"Index Fund Value: {account}")
        axes.grid(True)
        axes.legend(loc="best")
        figure.tight_layout()

        plot_canvas = FigureCanvasTkAgg(figure, master=plot_frame)
        plot_canvas.draw()
        plot_canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

    if len(accounts) == 0:
        no_data_label = ttk.Label(plot_frame, text="No data")
        no_data_label.pack()
        return

    update_date_entries_for_account(account_option.get())
    apply_settings()


class IndexFundsTab(tab.Tab):
    """Class implementing the Tab interface for index fund plotting."""

    def init(
        self, notebook, transactions, by_account, by_category, resample_rule, verbose
    ):
        print("IndexFundsTab.init")
        init_tab(notebook, transactions)


def get_tab():
    return IndexFundsTab()
