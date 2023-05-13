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

# Plotting
plt.figure(figsize=(10, 6))

# Plot a curve for each account
for account, data in grouped:
    plt.plot(data['date'], data['amount'], marker='o', linestyle='-', label=account)

plt.xlabel('Date')
plt.ylabel('Amount')
plt.title('Amount over Time by Account')
plt.grid(True)
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.show()
