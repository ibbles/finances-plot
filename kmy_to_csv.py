import argparse
import traceback
import sys
import xml.etree.ElementTree as ET
import pandas as pd

# This script converts an KMyMoney XML file to a CSV file that we can plot.
# To convert a KMY file to an XML file use 'zcat' as follows:
#   zcat MyFinancials.kmy > MyFinancials.xml

# The generated CSV file includes the following columns:
# - date: In %Y-%m-%d format.
# - amount: The amount of money moved.
# - account: The name of the account modified.
# - category: The expense category. Not included for transfers.

# How KMyMoney XML files work:
# - Every piece of data has an ID.
#   - IDs are integers with a one-character prefix.
#   - The prefix identifies the type.
#   - A: Account.
#   - I: Institution.
#   - P: Payee.
#   - R: Report.
#   - S: Split transaction.
#   - T: Transaction.
# - Every transaction is split in at least two parts.
# - One part handles decrement of the source account.
# - The other part handles increment of the target account.
# - Both parts have the same amount/value but opposite signs.
#   - Or if there are more than two parts, the parts' values sum to zero.
# - Payees are not accounts.
# - Categories are accounts.
#   - So a regular purchase is a transfer from a regular account to a category account.
# - A transaction include the payee that the payment is made to.
# - Every transaction has (What was I about to write here?)
# - Values are not written as real numbers, they are written as quotients.
#   - I assume to avoid floating point oddities.
# - Accounts and payees are referenced using IDs.
#   - Account IDs have an 'A' prefix.
#   - Payee IDs have a 'P' prefix.

# KMY to CSV map:
#
# --------------------------------------
# | CSV        | XML                   |
# |------------------------------------|
# | date       | TRANSACTION.postdate  |
# | amount     | SPLIT.value           |
# | account    | SPLIT.account (1st)   |
# | category   | SPLIT.account (2nd)   |
# | payee      | SPLIT.payee (both)    |
# --------------------------------------
#
# The account/category separation becomes more complicated when a transaction
# is split into more than two parts.


def get_value(split, transaction_id):
    """Read a quotient value and evaluate the expression to a floating point value."""
    value_expr = split.get("value")
    if value_expr is None:
        print(f"Valid value in transaction {transaction_id}: Value is None.")
        return None

    values = value_expr.split("/")
    if len(values) != 2:
        print(
            f"Invalid value in transaction {transaction_id}: "
            f"Fraction contains {len(values)} values, expected 2."
        )
        return None

    value = int(values[0]) / int(values[1])
    return value


def sign(v):
    """Return -1, 0, or 1 for negative, zero, and positive v, respectively."""
    return 1 if v > 0 else (-1 if v < 0 else 0)


def xml_to_csv(xml_file):
    """Converts the XML at the given path to a CSV file."""

    # Parse the XML file.
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Map account ID -> account name.
    # Accounts are those that are of type Asset and Equity.
    # Asset are stuff that is owned, such as money in the bank.
    # Not sure what Equity is, seems to be stuff that just exists out of nothing.
    accounts = {}
    for accounts_elem in root.findall("./ACCOUNTS"):
        for account_elem in accounts_elem.findall("./ACCOUNT"):
            parent_account = account_elem.get("parentaccount")
            if parent_account != "AStd::Asset" and parent_account != "AStd::Equity":
                # Any other parent account means that this is a category.
                # At least in my KMY file, there may be other types of accounts
                # that I'm not using yet.
                continue
            id_ = account_elem.get("id")
            name = account_elem.get("name")
            accounts[id_] = name

    # Map account ID (actually a category) -> {category name, parent ID}.
    categories = {}
    for accounts_elem in root.findall("./ACCOUNTS"):
        for account_elem in accounts_elem.findall("./ACCOUNT"):
            parent_account = account_elem.get("parentaccount")
            # TODO Skip this account if the root parent acount isn't 'AStd::Expense'.
            id_ = account_elem.get("id")
            name = account_elem.get("name")
            categories[id_] = {"name": name, "parent": parent_account}

    # Map payee ID -> payee name.
    payees = {}
    for payees_elem in root.findall("./PAYEES"):
        for payee_elem in payees_elem.findall("./PAYEE"):
            id_ = payee_elem.get("id")
            name = payee_elem.get("name")
            payees[id_] = name

    # Extract transactions from XML.
    transactions = []
    for transaction_elem in root.findall("./TRANSACTIONS/TRANSACTION"):
        transaction_id = transaction_elem.get("id")

        splits = transaction_elem.findall(".//SPLIT")
        if len(splits) < 2:
            print(
                f"Invalid split in transaction {transaction_id}: "
                f"Found {len(splits)} splits, expected at least 2."
            )
            continue

        try:
            account_split = splits[0]
            if not account_split.get("account") in accounts:
                print(
                    f"Invalid transaction {transaction_id}: "
                    "Expected the first split to be an account."
                )
                continue

            account_name = accounts[account_split.get("account")]
            account_value = get_value(account_split, transaction_id)
            if account_value == 0:
                continue

            if len(splits) == 2 and splits[1].get("account") in accounts:
                # This is an internal transfer between two accounts. Record both
                # halves. Except for 'Opening Balances' accounts. That's magic
                # money that we don't track. That's the money that we had before
                # we started tracking.
                if accounts[splits[0].get("account")] != "Opening Balances":
                    transactions.append(
                        {
                            "date": transaction_elem.get("postdate"),
                            "amount": get_value(splits[0], transaction_id),
                            "account": accounts[splits[0].get("account")],
                            "category": "",  # Internal transfers don't have a category.
                            "payee": "",  # Internal transfers don't have a payee.
                            "memo": splits[0].get("memo"),
                        }
                    )
                if accounts[splits[1].get("account")] != "Opening Balances":
                    transactions.append(
                        {
                            "date": transaction_elem.get("postdate"),
                            "amount": get_value(splits[1], transaction_id),
                            "account": accounts[splits[1].get("account")],
                            "category": "",  # Internal transfers don't have a category.
                            "payee": "",  # Internal transfers don't have a payee.
                            "memo": splits[0].get("memo"),
                        }
                    )
            else:
                # Assume this is one or more transaction(s) to/from a single
                # account to one or more categories. The most common case is
                # a regular purchase, where money is transferred from an account
                # to a category. Sometimes things from multiple categories are
                # purchased as part of a single transaction, For example when
                # buying both food and cloths. In this case the account would
                # be decreased by the entire cost, the Cloths category would
                # increase by the part of the price that was for the clothes
                # and the the Groceries category would increase by the part of
                # the price that was for the food.
                #
                # The increase in the categories must equal the decrease in the
                # account.
                #
                # Currently do not support purchases that take money from
                # multiple accounts.

                # The total cost of the purchase, i.e. the sum of all category
                # splits.
                summed_value = 0

                # Loop over the category splits. This assumes that the account
                # split is always the first (0:th) one, the one we slice past.
                for split in splits[1:]:
                    if split.get("account") in accounts:
                        print(
                            f"Invalid transaction {transaction_id}: "
                            "Expected non-first split to not be an account."
                        )
                        continue

                    category_name = categories[split.get("account")]["name"]
                    value = get_value(split, transaction_id)
                    if sign(value) == sign(account_value):
                        print(
                            f"Invalid transaction {transaction_id}: "
                            "Expected all non-account splits to have the opposite value sign."
                        )
                        continue

                    summed_value += value

                    transactions.append(
                        {
                            "date": transaction_elem.get("postdate"),
                            # Value negated because we record the account side
                            # but value is from the category side.
                            "amount": -value,
                            "account": account_name,
                            "category": category_name,
                            "payee": payees.get(split.get("payee"), ""),
                            "memo": split.get("memo"),
                        }
                    )

                if summed_value != -account_value:
                    print(
                        f"Invalid transaction {transaction_id}: "
                        "Expected the category splits to sum to the value of the account split."
                    )
                    continue

        except Exception as e:
            print(
                f"Found invalid transaction {transaction_id}: "
                f"Caught exception {e} {type(e)}"
            )
            traceback.print_exception(*sys.exc_info())

    # CSV data gathering complete, write to file.
    df = pd.DataFrame(transactions)
    df.to_csv("output.csv", sep=";", index=False)


def xml_to_csv__gpt(xml_file):
    # Parse the XML file.
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Extract data from XML
    transactions = []
    for transaction_elem in root.findall(".//TRANSACTION"):
        transaction_data = {
            "id": transaction_elem.get("id"),
            "postdate": transaction_elem.get("postdate"),
        }
        for split_elem in transaction_elem.findall(".//SPLIT"):
            split_data = {
                "id": split_elem.get("id"),
                "account": split_elem.get("account"),
                "value": split_elem.get("value"),
            }
            transaction_data.setdefault("splits", []).append(split_data)
        transactions.append(transaction_data)

    # Convert data to DataFrame
    data = []
    for transaction in transactions:
        for split in transaction["splits"]:
            data.append(
                {
                    "transaction_id": transaction["id"],
                    "postdate": transaction["postdate"],
                    "split_id": split["id"],
                    "account": split["account"],
                    "value": split["value"],
                }
            )

    df = pd.DataFrame(data)

    # Save DataFrame to CSV
    df.to_csv("output.csv", index=False)


def main():
    # Parse command line arguments.
    parser = argparse.ArgumentParser(
        description="Convert a KMyMoney XML file to a CSV file."
    )
    parser.add_argument(
        "filename", help="The file containing the KMyMoney XML document."
    )
    args = parser.parse_args()
    filename = args.filename
    xml_to_csv(filename)


if __name__ == "__main__":
    main()
