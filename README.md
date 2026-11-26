# Auction Clerk

A small Django app for clerking an auction sale on a local network. It replaces a
manual clerking spreadsheet: a sales ledger, numbered bidders, per-bidder
checkout sheets, and spreadsheet exports.

## Features

- Multiple sale events, each with its own bidders and lots; delete an event from the sale list or its workspace (with confirmation).
- Pre-load lot numbers and items on their own screen (linked by a pill from the workspace); typing a lot number in Record a sale fills in the item and quantity.
- Quick entry of lots: enter the amount and buyer at sale time.
- Bidder picker accepts typed bidder numbers or names with autocomplete suggestions.
- Bidders are numbered from 1 within each event; names/phones can be added later.
- Live totals for the sale, each bidder, and unassigned lots.
- Printable checkout sheets: find one buyer by number/name, or print all at once.
- CSV and `.xlsx` export. The workbook mirrors the original spreadsheet:
  `Sales`, `Sales with names`, `Bidders`, `Lots`, and one numbered sheet per bidder.

## Documentation

- `USER_GUIDE.md` — day-to-day instructions for clerks.
- `TECHNICAL_MANUAL.md` — installation, port binding, file layout, configuration,
  backups, and troubleshooting.

## Running

From this directory:

```bash
../.venv/bin/python3 manage.py runserver 0.0.0.0:8000
```

Then open http://localhost:8000 on this machine, or
http://<this-machine-ip>:8000 from another device on the LAN.

Database: `db.sqlite3` in this directory. It is preserved across restarts. Back
it up before making changes. Only to intentionally start over, delete it and run:

```bash
../.venv/bin/python3 manage.py migrate
```

Dependencies are installed in the sibling `.venv` (`django` and `openpyxl`).
On first run, Django generates a private `.secret_key` file in this directory;
keep it out of source control and back it up with the database if you want
sessions to survive a reinstall. Set `DJANGO_SECRET_KEY` to override it.

## Tests

Run `../.venv/bin/python3 manage.py test clerk` from this directory. Django
uses a separate test database; the live sale records are not changed.
