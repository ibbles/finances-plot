import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

# Load the CSV file into a DataFrame
df = pd.read_csv('experiments.csv', delimiter=';')

# Remove any leading/trailing spaces from column names
df.columns = df.columns.str.strip()

# Convert the 'date' column to datetime format, handling invalid dates
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')

# Find the oldest valid date
oldest_date = df['date'].min()

# Replace NaT values (invalid dates) with the oldest valid date
df['date'] = df['date'].fillna(oldest_date)

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(df['date'], df['amount'], marker='o', linestyle='-', color='b')
plt.xlabel('Date')
plt.ylabel('Amount')
plt.title('Amount over Time')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
