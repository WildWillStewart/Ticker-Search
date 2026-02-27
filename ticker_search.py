"""
Stock Search — NASDAQ Trader symbol directory
Full ticker list (stocks, ETFs, etc.) from nasdaqtraded.txt.
Covers NASDAQ, NYSE, AMEX. No API key required.
"""
import os
import pickle
import tkinter as tk
from datetime import datetime, date
from urllib.request import Request, urlopen

# NASDAQ Trader symbol directory (all US tape: NASDAQ, NYSE, AMEX, etc.)
NASDAQ_TRADED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"


def get_stock_list(use_cache=True):
    """Build ticker list from NASDAQ Trader nasdaqtraded.txt.
    Set use_cache=False to always fetch fresh from NASDAQ."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(script_dir, exist_ok=True)
    cache_file = os.path.join(script_dir, "tickers_cache.pkl")

    if use_cache and os.path.exists(cache_file):
        cache_date = datetime.fromtimestamp(os.path.getmtime(cache_file)).date()
        if cache_date == date.today():
            try:
                with open(cache_file, "rb") as f:
                    stock_list = pickle.load(f)
                print(f"Loaded {len(stock_list)} symbols from cache")
                return stock_list
            except Exception as e:
                print(f"Error loading cache: {e}, fetching from NASDAQ...")
        else:
            print(f"Cache outdated ({cache_date}), fetching fresh data...")

    print("Fetching ticker list from NASDAQ Trader...")
    out = []

    try:
        req = Request(NASDAQ_TRADED_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"Failed to fetch NASDAQ symbol file: {e}") from e

    lines = raw.strip().splitlines()
    if not lines:
        raise ValueError("NASDAQ symbol file is empty")

    # Header: Nasdaq Traded|Symbol|Security Name|Listing Exchange|Market Category|ETF|Round Lot Size|Test Issue|...
    header = lines[0]
    parts = header.split("|")
    try:
        idx_symbol = parts.index("Symbol")
        idx_name = parts.index("Security Name")
        idx_test = parts.index("Test Issue") if "Test Issue" in parts else None
    except ValueError:
        idx_symbol = 1
        idx_name = 2
        idx_test = 7

    for line in lines[1:]:
        cols = line.split("|")
        if len(cols) <= max(idx_symbol, idx_name):
            continue
        if idx_test is not None and idx_test < len(cols) and cols[idx_test].strip().upper() == "Y":
            continue
        symbol = (cols[idx_symbol] or "").strip().upper()
        name = (cols[idx_name] or "").strip()
        if symbol:
            out.append((symbol, name))

    out.sort(key=lambda x: (x[0],))

    if not out:
        raise ValueError("No tickers parsed from NASDAQ symbol file.")

    print(f"Fetched {len(out)} symbols from NASDAQ Trader")

    if use_cache:
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(out, f)
            print(f"Saved to: {cache_file}")
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    return out


def get_priority(s, n, query):
    sl = s.lower()
    nl = n.lower()
    if sl == query:
        return 0
    elif sl.startswith(query):
        return 1
    elif query in sl:
        return 2
    elif query in nl:
        return 3
    else:
        return 4


def stock_search(use_cache=True):
    """Open stock search GUI and return selected ticker.
    Set use_cache=False to always fetch from NASDAQ."""
    stock_list = get_stock_list(use_cache=use_cache)
    print(f"Loaded {len(stock_list)} symbols")

    root = tk.Tk()
    root.title("Stock Search")
    root.geometry("800x400")
    root.configure(bg="#333333")

    selected_ticker = [None]

    entry_var = tk.StringVar()
    my_entry = tk.Entry(
        root, textvariable=entry_var, font=("Arial", 12),
        bg="#444444", fg="white", insertbackground="white"
    )
    my_entry.pack(pady=10)

    list_frame = tk.Frame(root, bg="#333333")
    list_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    my_list = tk.Listbox(
        list_frame, width=80, height=10, bg="#444444", fg="white",
        selectbackground="#666666", selectforeground="white",
        yscrollcommand=scrollbar.set, takefocus=True
    )
    my_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=my_list.yview)

    def update():
        my_list.delete(0, tk.END)
        query = entry_var.get().lower()
        if query:
            matches = [
                (s, n) for s, n in stock_list
                if query in s.lower() or query in n.lower()
            ]
            sorted_matches = sorted(
                matches,
                key=lambda x: (get_priority(x[0], x[1], query), x[0].lower())
            )
            for s, n in sorted_matches[:100]:
                label = f"{s} - {n}" if n else s
                my_list.insert(tk.END, label)
        else:
            for s, n in stock_list[:100]:
                label = f"{s} - {n}" if n else s
                my_list.insert(tk.END, label)

    def check(e):
        update()

    my_entry.bind("<KeyRelease>", check)

    def fillout(e):
        try:
            clicked_index = my_list.nearest(e.y)
            if clicked_index >= 0:
                selected = my_list.get(clicked_index)
                symbol = selected.split(" - ")[0]
                entry_var.set(symbol)
                my_list.selection_clear(0, tk.END)
                my_list.selection_set(clicked_index)
                my_list.activate(clicked_index)
        except Exception:
            if my_list.curselection():
                selected = my_list.get(my_list.curselection())
                symbol = selected.split(" - ")[0]
                entry_var.set(symbol)

    def select_ticker():
        if my_list.curselection():
            selected = my_list.get(my_list.curselection())
            symbol = selected.split(" - ")[0].strip().upper()
        else:
            symbol = entry_var.get().strip().upper()
        if symbol:
            selected_ticker[0] = symbol
            print(f"Selected ticker: {symbol}")
            root.quit()
            root.destroy()
        else:
            print("No ticker selected")

    def perform_search(e=None):
        select_ticker()

    def double_click_select(e):
        if my_list.curselection():
            selected = my_list.get(my_list.curselection())
            symbol = selected.split(" - ")[0].strip().upper()
            entry_var.set(symbol)
            select_ticker()

    my_list.bind("<Button-1>", fillout)
    my_list.bind("<Double-Button-1>", double_click_select)
    my_list.bind("<Return>", perform_search)
    my_entry.bind("<Return>", perform_search)

    run_button = tk.Button(
        root, text="Run Analysis", command=perform_search,
        font=("Arial", 11), bg="#555555", fg="white",
        activebackground="#666666", activeforeground="white",
        padx=20, pady=5
    )
    run_button.pack(pady=10)

    root.mainloop()
    return selected_ticker[0]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Stock Search — NASDAQ Trader (stocks, ETFs, all US tape)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Always fetch from NASDAQ, do not use cache",
    )
    args = parser.parse_args()
    stock_search(use_cache=not args.no_cache)
