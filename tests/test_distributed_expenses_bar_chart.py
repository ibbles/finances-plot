import importlib.util
import pathlib
import sys
import unittest


def require_module(name):
    if importlib.util.find_spec(name) is None:
        raise unittest.SkipTest(f"{name} is not installed")


for dependency in ("pandas", "matplotlib", "mplcursors", "tkcalendar"):
    require_module(dependency)

import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tabs.distributed_expenses_bar_chart import prepare_transactions_for_plot


class DistributedExpensesBarChartTests(unittest.TestCase):
    def test_chunks_from_before_selected_range_are_included(self):
        transactions = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2024-01-15"),
                    "amount": -6000,
                    "category": "Furniture",
                    "memo": "Sofa",
                },
            ]
        )

        result = prepare_transactions_for_plot(
            transactions=transactions,
            start_date=pd.Timestamp("2024-02-01"),
            end_date=pd.Timestamp("2024-03-31"),
            amount_threshold=2000,
            chunk_size=2000,
        )

        self.assertEqual(
            list(result["date"]),
            [pd.Timestamp("2024-02-01"), pd.Timestamp("2024-03-01")],
        )
        self.assertEqual(list(result["amount"]), [2000, 2000])
        self.assertEqual(list(result["memo"]), ["Sofa (2/3)", "Sofa (3/3)"])

    def test_chunks_outside_selected_range_are_not_included(self):
        transactions = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2024-01-15"),
                    "amount": -6000,
                    "category": "Furniture",
                    "memo": "Sofa",
                },
            ]
        )

        result = prepare_transactions_for_plot(
            transactions=transactions,
            start_date=pd.Timestamp("2024-03-01"),
            end_date=pd.Timestamp("2024-03-31"),
            amount_threshold=2000,
            chunk_size=2000,
        )

        self.assertEqual(list(result["date"]), [pd.Timestamp("2024-03-01")])
        self.assertEqual(list(result["amount"]), [2000])
        self.assertEqual(list(result["memo"]), ["Sofa (3/3)"])


if __name__ == "__main__":
    unittest.main()
