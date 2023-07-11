import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt

# Not sure if or when this is needed.
# import matplotlib
# matplotlib.use("TkAgg")

# Parse command line arguments.
parser = argparse.ArgumentParser(description="Plot data with time resolution")
# The file containing the exported account data.
parser.add_argument("filename")
# If plot points should be per day, week, month, etc.
parser.add_argument(
    "resolution",
    choices=["days", "weeks", "months", "quarters", "years"],
    help="time resolution for plotting (days, weeks, months, quarters, or years)",
)
args = parser.parse_args()

# Find the data file, either relative to the current working directory, or
# relative to this script file.
file_path = os.path.realpath(__file__)
dir_path = os.path.dirname(file_path)
if not os.path.isfile(args.filename):
    args.filename = os.path.join(dir_path, args.filename)

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
# entire data set.
oldest_date = df["date"].min()

# Replace NaT values (invalid dates) with the oldest valid date.
# This is typically the all-zero opening balance transactions.
df["date"] = df["date"].fillna(oldest_date)

# Remove rows with invalid dates and zero amounts.
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

# One figure containing two axes, one plotting the sum of the transactions per
# account per time unit, and another plotting the amount of money in the
# account.
fig, (in_and_out, balance) = plt.subplots(1, 2, figsize=(15, 6))

# Plot transactions in and out of each account, grouped by the time resolution.
for account, data in grouped:
    data_resampled = data.set_index("date").resample(resample_rule).sum()
    in_and_out.plot(
        data_resampled.index,
        data_resampled["amount"],
        marker="o",
        linestyle="-",
        label=account,
    )

in_and_out.set_xlabel("Date")
in_and_out.set_ylabel("Amount")
in_and_out.set_title("Amount over Time by Account (Individual Values)")
in_and_out.grid(True)
in_and_out.tick_params(axis="x", rotation=45)
in_and_out.legend()

# Plot the amount of money in each account, grouped by the time resolution.
for account, data in grouped:
    data_resampled = data.set_index("date").resample(resample_rule).sum()
    accumulated_balance = data_resampled["amount"].cumsum()
    balance.plot(
        data_resampled.index,
        accumulated_balance,
        marker="o",
        linestyle="-",
        label=account,
    )

balance.set_xlabel("Date")
balance.set_ylabel("Accumulated Balance")
balance.set_title("Accumulated Balance over Time by Account")
balance.grid(True)
balance.tick_params(axis="x", rotation=45)
balance.legend()

plt.tight_layout()
plt.show()
