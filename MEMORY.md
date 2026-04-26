# Project Memory

## 2026-04-26 Session

- Added `AGENTS.md` as a contributor guide for this repository.
- Fixed `tabs/distributed_expenses_bar_chart.py` so large expense chunking happens
  before date-range filtering. This preserves chunks from expenses before the
  selected display range while still showing bars only for the selected range.
- Extracted `prepare_transactions_for_plot()` from the nested GUI update flow so
  the data preparation behavior can be tested without opening Tkinter.
- Added `tests/test_distributed_expenses_bar_chart.py` with `unittest` coverage
  for including pre-range chunks and excluding chunks outside the selected range.
- The dev machine used during this session could run syntax checks but did not
  have `pandas`; the user ran the test suite on another machine and confirmed:
  `Ran 2 tests ... OK`. The user also manually tested the application and
  confirmed the chart behavior works as intended.

Collaboration notes: the user provided a precise bug description and a good
implementation hint, then validated the result in the environment that has the
runtime dependencies. This worked well. Future changes should continue to
separate GUI code from data transformations where practical, because it makes
behavior tests possible even for this Tkinter application.
