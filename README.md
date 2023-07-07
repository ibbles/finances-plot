
This application is used to plot various stuff about money.
It imports CSV files exported from [Skrooge](https://flathub.org/apps/org.kde.skrooge).

Export a CSV file from Scrooge using Top Menu Bar > File > Export.
To export a subset of the accounts open the Accounts tab and select the accounts to include before selecting Export.

This script require Pandas and Matplotlib.
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
➤ python3 $GIT_REPO/finances_plot.py
```

To latest use the application:
```shell
➤ source venv/bin/activate.fish
➤ python3 $GIT_REPO/finances_plot.py days
```
