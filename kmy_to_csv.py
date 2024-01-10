import argparse
import traceback
import sys
import xml.etree.ElementTree as ET
import pandas as pd

# Include the following columns:
# - date: In %Y-%m-%d format.
# - amount: The amount of money moved.
# - account: The name of the account modified.
# - category: The expence category. Not included for transfers.

# How kmy.xml files work:
# - Every piece of data has an ID.
#   - IDs are integers with a one-character prefix.
#   - The prefix identifies the type.
#   - A: Account.
#   - I: Institution.
#   - P: Payee.
#   - R: Report.
#   - S: Split transaction.
#   - T: Transaction.
# - Every transaction is split in two parts.
# - One part handles decrement of the source account.
# - The other part handles increment of the target account.
# - Both parts have the same amount/value.
# - Categories are accounts.
# - Payees are not accounts.
# - A transaction include the payee that the payment is made to.
# - Every transaction has
# - Values are not written as real numbers, they are written as fractions.
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


def get_value(split, transaction_id):
    value_expr = split.get('value')
    if value_expr is None:
        print(f"Valid value in transaction {transaction_id}: Value is None.")
        return None

    values = value_expr.split("/")
    if  len(values) != 2:
        print(f"Invalid value in transaction {transaction_id}: Fraction contains {len(values)} values, expected 2.")
        return None

    value = int(values[0]) / int(values[1])
    return value


def xml_to_csv(xml_file):
    # Parse the XML file.
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Map account ID -> account name.
    accounts = {}
    for accounts_elem in root.findall(".//ACCOUNTS"):
        for account_elem in accounts_elem.findall(".//ACCOUNT"):
            parent_account = account_elem.get('parentaccount')
            if parent_account != "AStd::Asset":
                continue
            id = account_elem.get('id')
            name = account_elem.get('name')
            accounts[id] = name

    # Map account ID (actually a category) -> {category name, parent ID}.
    categories = {}
    for accounts_elem in root.findall(".//ACCOUNTS"):
        for account_elem in accounts_elem.findall(".//ACCOUNT"):
            parent_account = account_elem.get('parentaccount')
            # TODO Skip this account if the root parent acount isn't 'AStd::Expense'.
            id = account_elem.get('id')
            name = account_elem.get('name')
            categories[id] = {'name': name, 'parent': parent_account}

    # Map payee ID -> payee name.
    payees = {}
    for payees_elem in root.findall('.//PAYEES'):
        for payee_elem in payees_elem.findall('.//PAYEE'):
            id = payee_elem.get('id')
            name = payee_elem.get('name')
            payees[id] = name

    # Extract transactions from XML.
    transactions = []
    for transaction_elem in root.findall('.//TRANSACTION'):
        transaction_id = transaction_elem.get('id')

        splits = transaction_elem.findall('.//SPLIT')
        if len(splits) != 2:
            print(f"Invalid split in transaction {transaction_id}: Found {len(splits)} splits, expected 2")
            continue

        try:
            first_is_account = splits[0].get('account') in accounts
            second_is_account = splits[1].get('account') in accounts

            if first_is_account and second_is_account:
                # This is an internal transfer, record both halves of the transaction.
                transactions.append({
                    'date': splits[0].get('postdate'),
                    'amount': get_value(splits[0], transaction_id),
                    'account': accounts[splits[0].get('account')],
                    'category': "", # Internal transfers don't have a category.
                    'payee': "" # Internal transfers don't have a payee.
                })
                transactions.append({
                    'date': splits[1].get('postdate'),
                    'amount': get_value(splits[1], transaction_id),
                    'account': accounts[splits[1].get('account')],
                    'category': "", # Internal transfers don't have a category.
                    'payee': "" # Internal transfers don't have a payee.
                })
            elif first_is_account and not second_is_account:
                # This is money going in or out, only record the account transaction.
                transactions.append({
                    'date': splits[0].get('postdate'),
                    'amount': get_value(splits[0], transaction_id),
                    'account': accounts[splits[0].get('account')],
                    'category': categories[splits[1].get('account')],
                    'payee': payees.get(splits[0].get('payee'), '')
                })
            elif not first_is_account and second_is_account:
                # This looks like a reverse external transaction. Can this happen?
                transactions.append({
                    'date': splits[1].get('postdate'),
                    'amount': get_value(splits[1], transaction_id),
                    'account': accounts[splits[1].get('account')],
                    'category': categories[splits[0].get('account')],
                    'payee': payees[splits[1].get('payee')]
                })
                print(f"Found reverse transaction {transaction_id}.")
            elif not first_is_account and not second_is_account:
                # No idea what this is.
                print(f"Found account-less transaction {transaction_id}.")
            else:
                # Should never happen.
                raise ValueError(f"Could not determine transaction type for transaction {transaction_id}.")
        except Exception as e:
            print(f"Found invalid transaction {transaction_id}: {e} {type(e)}")
            traceback.print_exception(*sys.exc_info())

    df = pd.DataFrame(transactions)
    df.to_csv('output.csv', sep=";", index=False)


def xml_to_csv__gpt(xml_file):
    # Parse the XML file.
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Extract data from XML
    transactions = []
    for transaction_elem in root.findall('.//TRANSACTION'):
        transaction_data = {'id': transaction_elem.get('id'),
                            'postdate': transaction_elem.get('postdate')}
        for split_elem in transaction_elem.findall('.//SPLIT'):
            split_data = {'id': split_elem.get('id'),
                          'account': split_elem.get('account'),
                          'value': split_elem.get('value')}
            transaction_data.setdefault('splits', []).append(split_data)
        transactions.append(transaction_data)

    # Convert data to DataFrame
    data = []
    for transaction in transactions:
        for split in transaction['splits']:
            data.append({
                'transaction_id': transaction['id'],
                'postdate': transaction['postdate'],
                'split_id': split['id'],
                'account': split['account'],
                'value': split['value']
            })

    df = pd.DataFrame(data)

    # Save DataFrame to CSV
    df.to_csv('output.csv', index=False)



def main():
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description="Convert a KMyMoney XML file to a CSV file.")
    parser.add_argument("filename", help="The file containing the KMyMoney XML document.")
    args = parser.parse_args()
    filename = args.filename
    xml_to_csv(filename)


if __name__ == "__main__":
    main()
