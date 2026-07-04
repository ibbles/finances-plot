import importlib.util
import pathlib
import sys
import unittest


def require_module(name):
    if importlib.util.find_spec(name) is None:
        raise unittest.SkipTest(f"{name} is not installed")


for dependency in ("pandas", "matplotlib", "tkcalendar"):
    require_module(dependency)

import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tabs.index_funds import (
    get_index_fund_accounts,
    prepare_index_fund_series,
    prepare_index_fund_series_for_accounts,
)


def make_transactions(rows):
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp(date),
                "amount": amount,
                "account": account,
                "category": category,
                "memo": memo,
            }
            for date, amount, account, category, memo in rows
        ]
    )


class IndexFundsTests(unittest.TestCase):
    def test_return_categories_change_value_without_principal(self):
        transactions = make_transactions(
            [
                ("2024-01-01", 1000, "Fund", "", ""),
                ("2024-02-01", 200, "Fund", "Avkastning", ""),
                ("2024-03-01", -50, "Fund", "Negativ avkastning", ""),
            ]
        )

        result = prepare_index_fund_series(
            transactions,
            "Fund",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-03-01"),
        )

        self.assertEqual(list(result["value"]), [1000, 1200, 1150])
        self.assertEqual(list(result["principal_basis"]), [1000, 1000, 1000])
        self.assertEqual(list(result["positive_returns"]), [0, 200, 150])

    def test_withdrawal_reduces_principal_before_returns(self):
        transactions = make_transactions(
            [
                ("2024-01-01", 1000, "Fund", "", ""),
                ("2024-02-01", 300, "Fund", "Avkastning", ""),
                ("2024-03-01", -1200, "Fund", "", ""),
            ]
        )

        result = prepare_index_fund_series(
            transactions,
            "Fund",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-03-01"),
        )

        self.assertEqual(result["value"].iloc[-1], 100)
        self.assertEqual(result["principal_basis"].iloc[-1], 0)
        self.assertEqual(result["positive_returns"].iloc[-1], 100)

    def test_market_loss_below_deposits_creates_principal_loss(self):
        transactions = make_transactions(
            [
                ("2024-01-01", 1000, "Fund", "", ""),
                ("2024-02-01", -300, "Fund", "Negativ avkastning", ""),
            ]
        )

        result = prepare_index_fund_series(
            transactions,
            "Fund",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-02-01"),
        )

        self.assertEqual(result["value"].iloc[-1], 700)
        self.assertEqual(result["deposit_value"].iloc[-1], 700)
        self.assertEqual(result["principal_loss"].iloc[-1], 300)

    def test_prior_transactions_affect_visible_range(self):
        transactions = make_transactions(
            [
                ("2023-01-01", 1000, "Fund", "", ""),
                ("2023-02-01", 100, "Fund", "Avkastning", ""),
                ("2024-01-01", 200, "Fund", "", ""),
            ]
        )

        result = prepare_index_fund_series(
            transactions,
            "Fund",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-02-01"),
        )

        self.assertEqual(
            list(result["date"]),
            [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01")],
        )
        self.assertEqual(list(result["value"]), [1300, 1300])
        self.assertEqual(list(result["principal_basis"]), [1200, 1200])

    def test_other_account_rows_are_ignored_even_when_memo_mentions_fund(self):
        transactions = make_transactions(
            [
                ("2024-01-01", -500, "Buffer", "", "Rebalansering till Fund"),
                ("2024-01-01", 500, "Fund", "", "Rebalansering"),
                ("2024-02-01", 50, "Fund", "Avkastning", ""),
            ]
        )

        result = prepare_index_fund_series(
            transactions,
            "Fund",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-02-01"),
        )

        self.assertEqual(result["value"].iloc[-1], 550)
        self.assertEqual(result["principal_basis"].iloc[-1], 500)

    def test_same_day_rows_preserve_input_order_and_collapse_to_one_point(self):
        transactions = make_transactions(
            [
                ("2024-01-01", 1000, "Fund", "", ""),
                ("2024-02-01", 100, "Fund", "Avkastning", ""),
                ("2024-02-01", 50, "Fund", "", "Rebalansering"),
            ]
        )

        result = prepare_index_fund_series(
            transactions,
            "Fund",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-02-01"),
        )

        self.assertEqual(
            list(result["date"]),
            [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01")],
        )
        self.assertEqual(result["value"].iloc[-1], 1150)
        self.assertEqual(result["principal_basis"].iloc[-1], 1050)

    def test_account_choices_prefer_accounts_with_return_rows(self):
        transactions = make_transactions(
            [
                ("2024-01-01", -500, "Buffer", "", "Rebalansering till Fund"),
                ("2024-01-01", 500, "Fund", "", "Rebalansering"),
                ("2024-02-01", 50, "Fund", "Avkastning", ""),
            ]
        )

        self.assertEqual(get_index_fund_accounts(transactions), ["Fund"])

    def test_combined_series_sums_overlapping_funds(self):
        transactions = make_transactions(
            [
                ("2024-01-01", 1000, "Fund A", "", ""),
                ("2024-02-01", 100, "Fund A", "Avkastning", ""),
                ("2024-01-01", 2000, "Fund B", "", ""),
                ("2024-02-01", -200, "Fund B", "Negativ avkastning", ""),
            ]
        )

        result = prepare_index_fund_series_for_accounts(
            transactions,
            ["Fund A", "Fund B"],
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-02-01"),
        )

        self.assertEqual(list(result["value"]), [3000, 2900])
        self.assertEqual(list(result["principal_basis"]), [3000, 3000])
        self.assertEqual(list(result["deposit_value"]), [3000, 2900])
        self.assertEqual(list(result["positive_returns"]), [0, 0])
        self.assertEqual(list(result["principal_loss"]), [0, 100])

    def test_combined_series_handles_non_overlapping_fund_histories(self):
        transactions = make_transactions(
            [
                ("2024-01-01", 1000, "Fund A", "", ""),
                ("2024-02-01", 100, "Fund A", "Avkastning", ""),
                ("2024-03-01", 2000, "Fund B", "", ""),
                ("2024-04-01", 200, "Fund B", "Avkastning", ""),
            ]
        )

        result = prepare_index_fund_series_for_accounts(
            transactions,
            ["Fund A", "Fund B"],
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-04-01"),
        )

        self.assertEqual(
            list(result["date"]),
            [
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-02-01"),
                pd.Timestamp("2024-03-01"),
                pd.Timestamp("2024-04-01"),
            ],
        )
        self.assertEqual(list(result["value"]), [1000, 1100, 3100, 3300])
        self.assertEqual(list(result["principal_basis"]), [1000, 1000, 3000, 3000])
        self.assertEqual(list(result["positive_returns"]), [0, 100, 100, 300])

    def test_combined_series_ignores_counterpart_account_rows(self):
        transactions = make_transactions(
            [
                ("2024-01-01", -1000, "Buffer", "", "Rebalansering to Fund A"),
                ("2024-01-01", 1000, "Fund A", "", ""),
                ("2024-02-01", 100, "Fund A", "Avkastning", ""),
                ("2024-01-01", -2000, "Buffer", "", "Rebalansering to Fund B"),
                ("2024-01-01", 2000, "Fund B", "", ""),
                ("2024-02-01", 200, "Fund B", "Avkastning", ""),
            ]
        )

        result = prepare_index_fund_series_for_accounts(
            transactions,
            ["Fund A", "Fund B"],
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-02-01"),
        )

        self.assertEqual(result["value"].iloc[-1], 3300)
        self.assertEqual(result["principal_basis"].iloc[-1], 3000)
        self.assertEqual(result["positive_returns"].iloc[-1], 300)


if __name__ == "__main__":
    unittest.main()
