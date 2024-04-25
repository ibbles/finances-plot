""" A tab showing the balance in each account over time."""

import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import tab


def init_tab(notebook, grouped, resample_rule):
    """Create the tab and its constituent widgets."""

    # A Figure plotting the amount of money in each account.
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="Balance")

    # Plot the amount of money in each account, grouped by the time resolution.
    balance_fig, balance_ax = plt.subplots(figsize=(8, 4))
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

    panes = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
    panes.pack(expand=True, fill=tk.BOTH)

    canvas = FigureCanvasTkAgg(balance_fig, master=panes)
    canvas.draw()

    settings_frame = ttk.Frame(panes)
    panes.add(settings_frame)

    def make_update_plot(state_var, canvas, ax):
        def update_plot():
            print("Updating plot.")

        return update_plot

    checkbox_var = tk.BooleanVar()
    checkbox = ttk.Checkbutton(
        settings_frame,
        text="Enable Plot Update",
        variable=checkbox_var,
        command=make_update_plot(checkbox_var, canvas, balance_ax),
    )
    checkbox.grid(row=0, column=0, sticky=tk.W)

    panes.add(canvas.get_tk_widget())


class BalanceTab(tab.Tab):
    """Class implementing the Tab interface, populating itself with a balance tab."""

    def init(self, notebook, transactions, by_account, resample_rule):
        print("BalanceTab.init")
        init_tab(notebook, by_account, resample_rule)


def get_tab():
    return BalanceTab()
