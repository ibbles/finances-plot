import tab

import matplotlib.pyplot as plt
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk


def init_tab(notebook, grouped, resample_rule):
    # Create a Frame for each tab.
    transactions_tab = ttk.Frame(notebook)
    notebook.add(transactions_tab, text="Transactions")

    # One figure plotting the sum of the transactions per
    # account per time unit.
    transactions_fig, transactions_ax = plt.subplots(figsize=(8, 4))

    # Plot transactions in and out of each account, grouped by the time resolution.
    for account, data in grouped:
        data_resampled = data.set_index("date").resample(resample_rule).sum()
        transactions_ax.plot(
            data_resampled.index,
            data_resampled["amount"],
            marker="o",
            linestyle="-",
            label=account,
        )

    transactions_ax.set_xlabel("Date")
    transactions_ax.set_ylabel("Amount")
    transactions_ax.set_title("Amount over Time by Account (Individual Values)")
    transactions_ax.grid(True)
    transactions_ax.tick_params(axis="x", rotation=45)
    transactions_ax.legend()

    # Embed the matplotlib plot into the tab
    canvas = FigureCanvasTkAgg(transactions_fig, master=transactions_tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


class TransactionsTab(tab.Tab):
    def init(self, notebook, transactions, by_account, resample_rule):
        print("TransactionsTab.init")
        init_tab(notebook, by_account, resample_rule)


def get_tab():
    return TransactionsTab()
