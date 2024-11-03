
This application is used to plot various stuff about money.
It imports CSV files exported from [Skrooge](https://flathub.org/apps/org.kde.skrooge) or converted from KMyMoney.

Export a CSV file from Scrooge using Top Menu Bar > File > Export.
To export a subset of the accounts open the Accounts tab and select the accounts to include before selecting Export.

Use `zcat` together with the included `kmy_to_csv.py` script to translate a KMyMoney file:
```shell
zcat MyFinances.kmy > MyFinances.xml
python3 kmy_to_csv.py MyFinances.xml
```

This script require tkinter, Pandas and Matplotlib.
Virtual environment setup on Ubuntu 22.04:
```shell
➤ sudo apt install python3-venv
➤ python3 -m venv venv
➤ source venv/bin/activate.fish
➤ pip3 install pandas matplotlib

# Depending on your OS / Linux distribution you need to do one of these:

# Option 1
➤ pip3 install tkinter
# Option 2 - Ubuntu 22.04.
➤ sudo apt install python3-tk

# Run the script.
➤ python3 $GIT_REPO/finances_plot.py CSV_FILENAME months
```

To later use the application:
```shell
➤ source venv/bin/activate.fish
➤ python3 $GIT_REPO/finances_plot.py CSV_FILENAME months
```


Some tabs require additional libraries:
- `pip3 install mplcursors`
  - Used to create cursor hover pop-ups on plots.
  - Doesn't work with `PolyCollection`, which is used by `stackplot`.
- `pip3 install bokeh`
  - An entire plotting tool, alternative to matplotlib.
  - Opens in a web browser.
