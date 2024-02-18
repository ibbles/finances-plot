import pandas as pd
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# Define the plot types and their titles
plot_types = {
    "individual": "Amount over Time by Account (Individual Values)",
    "accumulated": "Accumulated Balance over Time by Account",
}

# Create the main Tkinter window
window = tk.Tk()
window.title("Finances Plot")
window.geometry("800x600")

# Create the Notebook widget for the tabs
notebook = ttk.Notebook(window)
notebook.pack(fill=tk.BOTH, expand=True)

# Parse the command line arguments to get the filename and resolution
filename = "ibbles.csv"
resolution = "D"

# Load the CSV file into a DataFrame
df = pd.read_csv(filename, delimiter=";")

# Remove any leading/trailing spaces from column names
df.columns = df.columns.str.strip()

# Convert the 'date' column to datetime format, handling invalid dates
df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")

# Find the oldest valid date. This will be used as the starting date for the entire data set
oldest_date = df["date"].min()

# Replace NaT values (invalid dates) with the oldest valid date
df["date"] = df["date"].fillna(oldest_date)

# Remove rows with invalid dates and zero amounts
df = df[(df["date"].notna()) & (df["amount"] != 0)]

# Group the rows by account
grouped = df.groupby("account")

# Create a tab for each plot type
for plot_type, plot_title in plot_types.items():
    # Create a Frame for each tab
    tab = ttk.Frame(notebook)
    notebook.add(tab, text=plot_type.capitalize())

    # Create the plot in the Frame
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_xlabel("Date")
    ax.set_ylabel("Amount")
    ax.set_title(plot_title)

    # Plot transactions in and out of each account, grouped by the time
    # resolution
    for account, data in grouped:
        data_resampled = data.set_index("date").resample(resolution).sum()
        ax.plot(
            data_resampled.index,
            data_resampled["amount"],
            marker="o",
            linestyle="-",
            label=account,
        )

    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    ax.legend()

    # Embed the matplotlib plot into the tab
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Select the first tab by default
notebook.select(0)


def close_window():
    print("Closing window.")
    window.quit()
    window.destroy()


window.protocol("WM_DELETE_WINDOW", close_window)
print("Close window callback configured.")

# Run the Tkinter event loop.
window.mainloop()
