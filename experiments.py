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
window.title("Finances Plot - Panes Experiment")
window.geometry("800x600")

# Create the Notebook widget for the tabs
notebook = ttk.Notebook(window)
notebook.pack(fill=tk.BOTH, expand=True)

# Parse the command line arguments to get the filename and resolution
filename = "ibbles.csv"
default_resolution = "D"

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


def plot_accounts(ax, resolution, plot_title):
    """
    Plot transactions in and out of each account, grouped by the time resolution
    """
    for account, data in grouped:
        data_resampled = data.set_index("date").resample(resolution).sum()
        ax.plot(
            data_resampled.index,
            data_resampled["amount"],
            marker="o",
            linestyle="-",
            label=account,
        )
    ax.set_xlabel("Date")
    ax.set_ylabel("Amount")
    ax.set_title(plot_title)
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)
    ax.legend()


# Create a tab for each plot type
for plot_type, plot_title in plot_types.items():
    # Create a Frame for each tab
    tab = ttk.Frame(notebook)
    notebook.add(tab, text=plot_type.capitalize())

    # Create the plot. Must be done early since widget callbacks need to
    # reference these.
    fig, ax = plt.subplots(figsize=(8, 4))
    plot_accounts(ax, default_resolution, plot_title)

    # Create a PanedWindow to hold the plot canvas and the settings frame
    panes = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
    panes.pack(expand=True, fill=tk.BOTH)

    canvas = FigureCanvasTkAgg(fig, master=panes)
    canvas.draw()

    # Create a Frame for settings
    settings_frame = ttk.Frame(panes)
    panes.add(settings_frame)

    # Create a callback function for the checkbox
    def make_update_plot(state_var, canvas, ax, plot_title):
        def update_plot():
            print("Checkbox state:", state_var.get())
            ax.clear()
            if state_var.get():
                plot_accounts(ax, "Y", plot_title)
            else:
                plot_accounts(ax, "D", plot_title)
            canvas.draw()

        return update_plot

    # Create the checkbox in the settings frame
    checkbox_var = tk.BooleanVar()
    checkbox = ttk.Checkbutton(
        settings_frame,
        text="Enable Plot Update",
        variable=checkbox_var,
        command=make_update_plot(checkbox_var, canvas, ax, plot_title),
    )
    checkbox.grid(row=0, column=0, sticky=tk.W)

    # Add the canvas and settings frame to the PanedWindow
    panes.add(canvas.get_tk_widget())


# Select the first tab by default
notebook.select(0)


def close_window():
    """Callback function registered with the WM_DELETE_WINDOW event."""
    window.quit()
    window.destroy()


window.protocol("WM_DELETE_WINDOW", close_window)


# Run the Tkinter event loop.
window.mainloop()
