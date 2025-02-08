"""Main application.

Creates the main window and populates it with a tab for each plugin.

Data is read from a CSV file where each line follows this pattern:
  date;amount;account;category;payee;memo

Example line:
  2024-01-22;-326.45;Martins kort;Vardagshandling;Coop Forum;Mat till nått.

If you use KMyMoney then a compatible CSV file can be created with zcat and
kmy_to_csv.py. For example, to convert the KMyMoney file MyFinances.kmy to
MyFinances.csv:

  $ zcat MyFinances.kmy > MyFinances.xml
  $ python3 kmy_to_csv.py MyFinances.xml


usage: finances_plot.py [-h] csv_filename {days,weeks,months,quarters,years}
"""

# System imports.
import argparse
import importlib
import os
import sys
import tkinter as tk
from tkinter import ttk

# Library imports
import pandas as pd

# Application imports.
import tab


def fail(message):
    """Terminate the application with an error message."""
    print(message, file=sys.stderr)
    sys.exit(1)


def get_app_root():
    """The install directory for the application."""
    file_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(file_path)
    return dir_path


def path_in_app_root(path):
    """Find resources within the install directory for the application."""
    return os.path.join(get_app_root(), path)


def load_tabs() -> list[tab.Tab]:
    """
    Search for plugins within the 'tabs' directory and create a tab for each.
    """

    # List of tab.Tab instances that has been loaded from a plugin module in the
    # tabs directory.
    loaded_tabs: list[tab.Tab] = []

    tabs_path = path_in_app_root("tabs")

    # TODO: Will this walk recursively as-is, or do I need a recursive call for
    # each subdirectory?
    for dirpath, _, files in os.walk(tabs_path):
        # We can only import Python modules, i.e. plugins, in directories listed
        # in sys.path.
        if dirpath not in sys.path:
            sys.path.insert(0, dirpath)
        for file in files:
            # Check if the file looks like a tab plugin. For now assume that any
            # .py file is a tab plugin.
            (name, ext) = os.path.splitext(file)
            if not ext == os.extsep + "py":
                continue
            try:
                module = importlib.import_module(name)
                if hasattr(module, "get_tab"):
                    # The module is a tab plugin. Have it create its tab.
                    loaded_tab: tab.Tab = module.get_tab()
                    loaded_tabs.append(loaded_tab)
                else:
                    print(f"Error: Tab '{name}' does not have 'get_tab' function.")
            except ImportError as e:
                print(f"Error: Could not load tab '{name}': {e}")
            except SyntaxError as e:
                print(f"Error: Could not load tab '{name}': {e}")
                print(e.text)
                print(f'{" "*(e.offset - 1)}^{"~"*(e.end_offset - e.offset - 1)}')

    return loaded_tabs


def parse_arguments():
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description="Plot data with time resolution")
    parser.add_argument(
        "csv_filename", help="The CSV file containing the exported account data."
    )
    parser.add_argument(
        "resolution",
        choices=["days", "weeks", "months", "quarters", "years"],
        help="Time resolution for plotting.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable extra debug output."
    )
    args = parser.parse_args()
    return args


def main():
    """Main function."""

    args = parse_arguments()
    loaded_tabs: list[tab.Tab] = load_tabs()

    # Find the data file, either relative to the current working directory, or
    # relative to the application install directory.
    filename = args.csv_filename
    if not os.path.isfile(filename):
        # Did not find relative to current directory, try relative to the
        # application install directory.
        filename = path_in_app_root(filename)
    if not os.path.isfile(filename):
        fail(f"Could not open file '{args.filename}'. Also tried '{filename}'.")

    # The CSV file we are working on has the following format:
    #
    #   date;amount;account;category;payee;memo
    #
    # It is created by kmy_to_csv.py. It reads an XML file created from the
    # KMyMoney file. The XML file is created with:
    #
    #   zcat MyFinances.kmy > MyFinances.xml
    #
    # Each row, except for the heading, contains one endpoint of a transaction.
    # Most transactions have two endpoints: the source and the destination.
    # However, we only record our own accounts so any transactions that have an
    # endpoint elsewhere, such as a store, will only have one endpoint included
    # in the data. A transfer between two of our own accounts has two rows, one
    # for each account.
    #
    # The "date" column is given in "YYYY-MM-DD" format, a.k.a. '%Y-%m-%d'. Some
    # transactions have an all-zero date, the "amount" column then give the
    # opening balance for that account. There is exactly one such row for each
    # account and it is always the first row for that account.
    #
    # The "account" column is the name of the account that the current
    # transaction modifies. Transactions that involve multiple accounts, i.e.
    # transfers, consists of two or more rows, one for each account in the
    # transaction.

    # Load the CSV file into a DataFrame.
    df = pd.read_csv(filename, delimiter=";")

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

    df["memo"] = df["memo"].fillna("")

    # Remove rows with invalid dates and zero amounts.
    # NOTE: What would cause a transaction to have a zero amount?
    df = df[(df["date"].notna()) & (df["amount"] != 0)]

    # Group the rows by commonly used properties.
    by_account = df.groupby("account")
    by_category = df.groupby("category")

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
    window.geometry("1920x1080")

    # Create the Notebook widget for the tabs.
    notebook = ttk.Notebook(window)
    notebook.pack(fill=tk.BOTH, expand=True)

    # for tab in tabs.values():
    for loaded_tab in loaded_tabs:
        loaded_tab.init(
            notebook, df, by_account, by_category, resample_rule, args.verbose
        )

    def close_window():
        window.quit()
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", close_window)

    # Run the Tkinter event loop.
    window.mainloop()


if __name__ == "__main__":
    main()
