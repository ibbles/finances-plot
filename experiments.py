import argparse
import pandas as pd
import matplotlib.pyplot as plt

# Parse command line arguments
parser = argparse.ArgumentParser(description='Plot data with time resolution')
parser.add_argument('resolution', choices=['days', 'weeks', 'months', 'quarters', 'years'],
                    help='time resolution for plotting (days, weeks, months, quarters, or years)')
args = parser.parse_args()

# Load the CSV file into a DataFrame
df = pd.read_csv('your_file.csv', delimiter=';')

# Remove any leading/trailing spaces from column names
df.columns = df.columns.str.strip()

# Convert the 'date' column to datetime format, handling invalid dates
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')

# Find the oldest valid date
oldest_date = df['date'].min()

# Replace NaT values (invalid dates) with the oldest valid date
df['date'] = df['date'].fillna(oldest_date)

# Remove rows with invalid dates and zero amounts
df = df[(df['date'].notna()) & (df['amount'] != 0)]

# Group the rows by account
grouped = df.groupby('account')

# Dictionary to map resolution options to resample rule parameters
resolution_mapping = {
    'days': 'D',
    'weeks': 'W',
    'months': 'M',
    'quarters': 'Q',
    'years': 'A'
}

# Get the resample rule parameter based on the selected resolution
resample_rule = resolution_mapping[args.resolution]

# Plotting both figures
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Plot individual value curves for each account
for account, data in grouped:
    data_resampled = data.set_index('date').resample(resample_rule).sum()
    ax1.plot(data_resampled.index, data_resampled['amount'], marker='o', linestyle='-', label=account)

ax1.set_xlabel('Date')
ax1.set_ylabel('Amount')
ax1.set_title('Amount over Time by Account (Individual Values)')
ax1.grid(True)
ax1.tick_params(axis='x', rotation=45)
ax1.legend()

# Plot accumulated balance curves for each account
for account, data in grouped:
    data_resampled = data.set_index('date').resample(resample_rule).sum()
    accumulated_balance = data_resampled['amount'].cumsum()
    ax2.plot(data_resampled.index, accumulated_balance, marker='o', linestyle='-', label=account)

ax2.set_xlabel('Date')
ax2.set_ylabel('Accumulated Balance')
ax2.set_title('Accumulated Balance over Time by Account')
ax2.grid(True)
ax2.tick_params(axis='x', rotation=45)
ax2.legend()

plt.tight_layout()
plt.show()
