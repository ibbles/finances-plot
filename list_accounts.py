
import argparse
import xml.etree.ElementTree as ET
import pandas as pd

# To convert a kmy file to an XML file:
#   zcat MyFinancials.kmy > MyFinancials.xml

def xml_to_csv(xml_file):
    # Parse the XML file.
    tree = ET.parse(xml_file)
    root = tree.getroot()

    accounts = []
    categories = []
    for account_elem in root.findall('./ACCOUNTS/ACCOUNT'):
        account_data = {
            'parent': account_elem.get('parentaccount'),
            'id': account_elem.get('id'),
            'name': account_elem.get('name'),
        }
        if account_data['parent'] == "AStd::Asset":
            accounts.append(account_data)
        else:
            categories.append(account_data)

    print(" CATEGORIES:")
    for category in categories:
        print(f"id: {category['id']}, name: {category['name']}")
    print(" ACCOUNTS:")
    for account in accounts:
        print(f"id: {account['id']}, name: {account['name']}")


def main():
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description="Convert a KMyMoney XML file to a CSV file.")
    parser.add_argument("filename", help="The file containing the KMyMoney XML document.")
    args = parser.parse_args()
    filename = args.filename
    xml_to_csv(filename)


if __name__ == "__main__":
    main()
