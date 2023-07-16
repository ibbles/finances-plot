import tab

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import pandas as pd


def init_tab(notebook, df, resample_rule):
    # Create a Frame for the tab.
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Category Chart")

    # Create a matplotlib figure.
    fig, ax = plt.subplots(figsize=(8, 4))

    # Populate 'fig' and/or 'ax' here.
    df = df.set_index("date")
    # df = df.droplevel("category")

    df_by_category = df.resample(resample_rule)["amount"].sum().unstack()
    df_by_category.plot(kind="bar", ax=ax)

    # Embed the matplotlib plot into the tab.
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


class CategoryTab(tab.Tab):
    def init(self, notebook, transactions, by_account, resample_rule):
        print("CategoryTab.init")
        init_tab(notebook, transactions, resample_rule)


def get_tab():
    return CategoryTab()
