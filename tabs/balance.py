import tab

import matplotlib.pyplot as plt
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk


def init_tab(notebook, grouped, resample_rule):
    # A Figure plotting the amount of money in each account.
    balance_tab = ttk.Frame(notebook)
    notebook.add(balance_tab, text="Balance")
    balance_fig, balance_ax = plt.subplots(figsize=(8, 4))

    # Plot the amount of money in each account, grouped by the time resolution.
    for account, data in grouped:
        data_resampled = data.set_index("date").resample(resample_rule).sum()
        accumulated_balance = data_resampled["amount"].cumsum()
        balance_ax.plot(
            data_resampled.index,
            accumulated_balance,
            marker="o",
            linestyle="-",
            label=account,
        )

    balance_ax.set_xlabel("Date")
    balance_ax.set_ylabel("Accumulated Balance")
    balance_ax.set_title("Accumulated Balance over Time by Account")
    balance_ax.grid(True)
    balance_ax.tick_params(axis="x", rotation=45)
    balance_ax.legend()

    # Embed the matplotlib plot into the tab
    canvas = FigureCanvasTkAgg(balance_fig, master=balance_tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


class BalanceTab(tab.Tab):
    def init(self, notebook, grouped, resample_rule):
        print("BalanceTab.init")
        init_tab(notebook, grouped, resample_rule)


def get_tab():
    return BalanceTab()
