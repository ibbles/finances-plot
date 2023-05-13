import pandas as pd
import matplotlib.pyplot as plt

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

# Group the rows by account
grouped = df.groupby('account')

# Plotting both figures
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Plot individual value curves for each account
for account, data in grouped:
    ax1.plot(data['date'], data['amount'], marker='o', linestyle='-', label=account)

ax1.set_xlabel('Date')
ax1.set_ylabel('Amount')
ax1.set_title('Amount over Time by Account (Individual Values)')
ax1.grid(True)
ax1.tick_params(axis='x', rotation=45)
ax1.legend()

# Plot accumulated balance curves for each account
for account, data in grouped:
    accumulated_balance = data['amount'].cumsum()
    ax2.plot(data['date'], accumulated_balance, marker='o', linestyle='-', label=account)

ax2.set_xlabel('Date')
ax2.set_ylabel('Accumulated Balance')
ax2.set_title('Accumulated Balance over Time by Account')
ax2.grid(True)
ax2.tick_params(axis='x', rotation=45)
ax2.legend()

plt.tight_layout()
plt.show()
