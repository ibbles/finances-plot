import argparse
import importlib
import matplotlib.pyplot as plt
import os
import pandas as pd
import sys
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import ttk

from tab import Tab


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def get_app_root():
    file_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(file_path)
    return dir_path


def path_in_app_root(path):
    return os.path.join(get_app_root(), path)


loaded_tabs = []


def load_tabs(path):
    path = path_in_app_root(path)
    for dirpath, dirs, files in os.walk(path):
        if dirpath not in sys.path:
            sys.path.insert(0, dirpath)
        for file in files:
            (name, ext) = os.path.splitext(file)
            if ext == os.extsep + "py":
                module = importlib.import_module(name)
                tab = module.get_tab()
                loaded_tabs.append(tab)


load_tabs("tabs")

# Parse command line arguments.
parser = argparse.ArgumentParser(description="Plot data with time resolution")
parser.add_argument("filename", help="The file containing the exported account data.")
parser.add_argument(
    "resolution",
    choices=["days", "weeks", "months", "quarters", "years"],
    help="Time resolution for plotting.",
)
args = parser.parse_args()

# Find the data file, either relative to the current working directory, or
# relative to this script file.
filename = args.filename
if not os.path.isfile(filename):
    file_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(file_path)
    filename = os.path.join(dir_path, args.filename)
if not os.path.isfile(filename):
    fail(f"Could not open file '{args.filename}'. Also tried {filename}")

# The CSV file we are working on has the following format:
# "date";"bank";"account";"number";"mode";"payee";"comment";"quantity";"unit";"amount";"sign";"category";"status";"tracker";"bookmarked";"id";"idtransaction";"idgroup"
#
# Many columns are ignored.
#
# Each row, except for the heading, contains one transaction.
#
# The "date" column is given in "YYYY-MM-DD" format, a.k.a. '%Y-%m-%d'.
# Some transactions have an all-zero date, the "amount" column then give the
# opening balance for that account. There is exactly one such row for each
# account and it is always the first row for that account.
#
# The "account" column is the name of the account that the current transaction
# modifies. Transactions that involve multiple accounts, i.e. transfers,
# consists of two or more rows, for for each account in the group, and they are
# identified as a pair by having the same value in the "idgroup" column. All
# single-account transactions have a 0 in the "idgroup" column.
#
# The "quantity" and "amount" columns always contains the same value.


# Load the CSV file into a DataFrame.
df = pd.read_csv(args.filename, delimiter=";")

# Remove any leading/trailing spaces from column names.
df.columns = df.columns.str.strip()

# Convert the 'date' column to datetime format, handling invalid dates.
df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")

# Find the oldest valid date. This will be used as the starting date for the
# data set as a whole.
oldest_date = df["date"].min()

# Replace NaT values (invalid dates) with the oldest valid date.
# This is typically the all-zero opening balance transactions.
df["date"] = df["date"].fillna(oldest_date)

# Remove rows with invalid dates and zero amounts.
# NOTE: What would cause a transaction to have a zero amount?
df = df[(df["date"].notna()) & (df["amount"] != 0)]

# Group the rows by account.
grouped = df.groupby("account")

# Dictionary to map resolution options to resample rule parameters.
resolution_mapping = {
    "days": "D",
    "weeks": "W",
    "months": "M",
    "quarters": "Q",
    "years": "A",
}

# Get the resample rule parameter based on the selected resolution.
resample_rule = resolution_mapping[args.resolution]

# Create the main Tkinter window.
window = tk.Tk()
window.title("Finances Plot")
window.geometry("800x600")

# Create the Notebook widget for the tabs.
notebook = ttk.Notebook(window)
notebook.pack(fill=tk.BOTH, expand=True)

# for tab in tabs.values():
for tab in loaded_tabs:
    tab.init(notebook, grouped, resample_rule)


def close_window():
    window.quit()
    window.destroy()


window.protocol("WM_DELETE_WINDOW", close_window)

# Run the Tkinter event loop.
window.mainloop()
