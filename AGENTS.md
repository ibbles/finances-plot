# Repository Guidelines

## Project Structure & Module Organization

This is a small Python/Tkinter plotting application for finance CSV exports.
`finances_plot.py` is the main entry point: it loads a semicolon-delimited CSV,
normalizes dates, groups transactions, and initializes all tab plugins.
`tab.py` defines the base `Tab` interface. Active tab modules live in `tabs/`
and are auto-loaded when they are `.py` files exposing `get_tab()`.
Disabled or experimental tab files use suffixes such as `.disabled` or
`_disabled`. Utility scripts include `kmy_to_csv.py` for KMyMoney XML conversion,
`list_accounts.py`, and `experiments.py`. Sample CSV files are kept at the repo
root.

## Build, Test, and Development Commands

Create and activate a virtual environment before running the app:

```shell
python3 -m venv venv
source venv/bin/activate
pip install pandas matplotlib mplcursors tkcalendar bokeh
```

On Ubuntu, install Tkinter with `sudo apt install python3-tk` if it is missing.
Run the GUI locally with:

```shell
python3 finances_plot.py CSV_FILENAME months
python3 finances_plot.py test_export.csv months --verbose
```

Convert a KMyMoney file before plotting:

```shell
zcat MyFinances.kmy > MyFinances.xml
python3 kmy_to_csv.py MyFinances.xml
```

## Coding Style & Naming Conventions

Use Python 3 style with 4-space indentation, descriptive snake_case functions,
and PascalCase tab classes such as `TransactionsTab`. Keep imports grouped as
standard library, third-party libraries, then local modules. Prefer type
annotations for new shared functions, following the existing gradual typing in
`finances_plot.py`. New tab files should be lower_snake_case and implement
`get_tab()` returning a `tab.Tab` subclass.

## Testing Guidelines

Run automated tests with `python3 -m unittest discover -s tests`. Tests live in
`tests/` and use `test_*.py` naming. For changes, also run a manual smoke test
with `test_export.csv` or another known-good export and verify the relevant tab
opens without import errors. For converter changes, compare generated CSV
columns with the expected `date;amount;account;category;payee;memo` format.

## Commit & Pull Request Guidelines

Recent commits use short imperative messages, for example `Add --verbose flag`
or `Use side-specific time aliases for Pandas`. Keep commits focused on one
behavioral change. Pull requests should describe the user-visible effect, list
manual test commands and sample CSVs used, mention new dependencies, and include
screenshots when plot output or Tkinter layout changes.

## Security & Configuration Tips

Do not commit personal finance exports. Keep private CSV and KMyMoney files out
of git, and prefer sanitized sample data for debugging or reviews.

## Project Memory

Read `MEMORY.md` before non-trivial changes. It records useful context from
previous sessions, including confirmed behavior and collaboration notes.
