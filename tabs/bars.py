import tab

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import pandas as pd

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def init_tab(notebook, df, resample_rule):
    # Create a Frame for the tab.
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Category Bars")

    # Group the rows by category and resample based on the selected resolution.
    grouped = df.groupby("category")
    resampled_data = pd.DataFrame()

    for category, data in grouped:
        data_resampled = data.set_index("date").resample(resample_rule).sum()
        data_resampled["category"] = category
        resampled_data = pd.concat([resampled_data, data_resampled])

    # Create a bar chart showing transactions with different categories
    fig, ax = plt.subplots(figsize=(8, 4))
    categories = resampled_data["category"].unique()
    num_categories = len(categories)
    bar_width = 0.8 / num_categories
    colors = plt.cm.get_cmap("Set3").colors

    for i, category in enumerate(categories):
        category_data = resampled_data[resampled_data["category"] == category]
        ax.bar(
            category_data.index,
            category_data["amount"],
            width=bar_width,
            align="edge",
            label=category,
            color=colors[i % len(colors)],
        )

    ax.set_xlabel("Date")
    ax.set_ylabel("Amount")
    ax.set_title("Transaction Amount by Category")
    ax.legend()
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)

    # Embed the matplotlib plot into the tab
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


class BarsTab(tab.Tab):
    def init(self, notebook, transactions, by_account, resample_rule):
        print("BarsTab.init")
        init_tab(notebook, transactions, resample_rule)


def get_tab():
    return BarsTab()
