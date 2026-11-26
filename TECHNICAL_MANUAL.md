# Auction Clerk — Technical Manual

This manual covers installation, startup, port binding, code layout, data
storage, configuration, testing, backups, and troubleshooting.

For day-to-day use, see `USER_GUIDE.md`.

## 1. Scope and design

Auction Clerk is a Django application served over a LAN with Django's development
server. It is intentionally simple:

- one SQLite database file;
- no login/authentication;
- no external database server;
- no static build step;
- no separate frontend application;
- HTML forms, server-rendered templates, and a small amount of inline JavaScript.

It is intended for a trusted local network, not for public internet exposure.

## 2. Reference environment

A typical installation uses:

| Item | Value |
| --- | --- |
| OS | Ubuntu 24.04-based Linux |
| Python | 3.12.3 |
| Django | 6.1.3 |
| openpyxl | 3.1.5 |
| Web server | Django `runserver` |
| Bind address | `0.0.0.0:8000` |
| Database | SQLite, `db.sqlite3` |
| Project directory | `auction_clerk/` in your workspace |
| Virtual environment | `.venv/` as a sibling of `auction_clerk/` |

LAN addresses are assigned by DHCP and may change. Use `hostname -I` to discover
the current address.

## 3. Installation

### 3.1 Install from scratch

The app code is expected at `auction_clerk/` in your workspace.

The virtual environment is a sibling of that directory. From the parent directory
that contains `auction_clerk/`, create it if it does not exist:

```bash
python3 -m venv .venv
.venv/bin/python3 -m pip install --upgrade pip
.venv/bin/python3 -m pip install django==6.1.3 openpyxl==3.1.5
```

There is currently no `requirements.txt`; the pinned versions above are the
supported versions.

Make sure the launcher is executable:

```bash
chmod +x auction_clerk/run.sh
```

### 3.2 Initialize the database

Run migrations from the project directory:

```bash
cd auction_clerk
../.venv/bin/python3 manage.py migrate
```

`migrate` creates `db.sqlite3` if needed and is safe to run repeatedly. Existing
data is preserved.

Verify the installation:

```bash
../.venv/bin/python3 manage.py check
../.venv/bin/python3 manage.py showmigrations clerk
```

Expected applied migrations:

```text
0001_initial
0002_alter_sale_bidder
0003_remove_sale_payment_method
0004_cataloglot
```

Do not edit applied migration files by hand. If models change, generate a new
migration with `manage.py makemigrations clerk` and then apply it.

### 3.3 First launch

```bash
cd auction_clerk
./run.sh
```

Then open:

```text
http://localhost:8000
```

The database starts empty; no rows from the original spreadsheet are imported.

## 4. Starting and stopping the server

### Start

```bash
cd auction_clerk && ./run.sh
```

### Stop

If running in a terminal, press `Ctrl+C`.

If running in the background:

```bash
pkill -f "manage.py runserver 0.0.0.0:8000"
```

### Verify

```bash
ps -ef | grep '[m]anage.py runserver'
curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/
```

A response of `200` means the app answered.

### Restart safety

Starting and stopping the server does **not** delete data. All persistent data is
in `db.sqlite3`. Django's development server auto-reloads when Python files
change; database schema changes still require `manage.py migrate`.

The server does **not** automatically start after a reboot. Auto-start is not
configured; it would require a systemd service or startup entry.

## 5. Port binding and LAN access

`run.sh` executes:

```sh
exec ../.venv/bin/python3 manage.py runserver 0.0.0.0:8000
```

- `0.0.0.0` means "listen on every IPv4 interface on this machine".
- Clients do **not** connect to `0.0.0.0`. They connect to the machine's LAN IP.
- `8000` is the TCP port.

On the host machine:

```text
http://localhost:8000
```

On another LAN device:

```text
http://<host-ip>:8000
```

Find the host IP:

```bash
hostname -I
```

Check what is actually listening:

```bash
ss -ltnp | grep ':8000'
```

### Firewall

On Ubuntu with UFW:

```bash
sudo ufw status
sudo ufw allow 8000/tcp
```

For a tighter rule, allow only your LAN subnet, for example:

```bash
sudo ufw allow from 192.168.0.0/16 to any port 8000 proto tcp
```

### Changing the port

Temporary one-off run:

```bash
cd auction_clerk
../.venv/bin/python3 manage.py runserver 0.0.0.0:8001
```

Permanent change: edit the last line of `run.sh` to use the new port. Then update
firewall rules and browser bookmarks.

To bind only to the local machine, use `127.0.0.1:8000` instead of
`0.0.0.0:8000`.

Avoid running two servers against the same SQLite database at the same time.
Stop the old one before starting a replacement.

## 6. Configuration reference

Configuration lives in `clerk_site/settings.py`.

| Setting | Current value | Meaning |
| --- | --- | --- |
| `DEBUG` | `True` | Development error pages and auto-reload. Not suitable for production. |
| `ALLOWED_HOSTS` | `["*"]` | Accepts any Host header; convenient for LAN use. |
| `CSRF_TRUSTED_ORIGINS` | `["http://*"]` | Allows HTTP origins; HTTPS reverse proxies need explicit origins. |
| `INSTALLED_APPS` | contenttypes, sessions, messages, `clerk` | No Django admin app is installed. |
| `MIDDLEWARE` | security, sessions, common, CSRF, messages | Standard minimal middleware set. |
| `TEMPLATES` | `APP_DIRS=True` | Templates load from `clerk/templates/`. |
| `DATABASES["default"]` | SQLite at `BASE_DIR / "db.sqlite3"` | `timeout=20` reduces lock errors. |
| `TIME_ZONE` / `USE_TZ` | `UTC` / `True` | Datetimes stored in UTC. |
| `STATIC_URL` | `static/` | No static files are collected; CSS/JS are inline in `base.html`. |
| `MESSAGE_STORAGE` | session storage | Flash messages use the session table. |
| `WSGI_APPLICATION` / `ASGI_APPLICATION` | `clerk_site.*` | Present for completeness; not used by `runserver`. |

Security notes:

- `SECRET_KEY` is read from `DJANGO_SECRET_KEY` when set; otherwise a private
  `.secret_key` file is generated in the project directory the first time
  settings are loaded. That file is gitignored. Keep it private, and back it up
  with the database if you want sessions to survive a reinstall. Disable
  `DEBUG` before any non-LAN deployment.
- There is no authentication. Anyone who can reach the port can view and delete
  data.
- Do not expose port 8000 to the internet.

## 7. File structure

```text
workspace/
├── .venv/                         # Python virtual environment (shared by app)
│   └── lib/python3.12/site-packages/
│       ├── django/                # Django 6.1.3
│       └── openpyxl/              # openpyxl 3.1.5
│
└── auction_clerk/                 # Django project root
    ├── manage.py                  # Django management entry point
    ├── run.sh                     # Starts 0.0.0.0:8000 using ../.venv
    ├── README.md                  # Short project overview
    ├── USER_GUIDE.md              # End-user instructions
    ├── TECHNICAL_MANUAL.md        # This document
    ├── db.sqlite3                 # Live application database
    ├── .secret_key                # Locally generated secret (gitignored)
    │
    ├── clerk_site/                # Project configuration package
    │   ├── __init__.py
    │   ├── settings.py            # Settings described above
    │   ├── urls.py                # Root URL conf; includes clerk.urls
    │   ├── wsgi.py                # WSGI entry point (unused by runserver)
    │   └── asgi.py                # ASGI entry point (unused by runserver)
    │
    └── clerk/                     # Application package
        ├── __init__.py
        ├── apps.py                # App configuration
        ├── models.py              # Event, Bidder, CatalogLot, Sale
        ├── forms.py               # Model forms, validation, bidder/lot lookup
        ├── views.py               # Request handlers
        ├── urls.py                # Application URL patterns
        ├── exports.py             # CSV and XLSX generation
        ├── tests.py               # Django test suite
        ├── migrations/
        │   ├── 0001_initial.py
        │   ├── 0002_alter_sale_bidder.py
        │   ├── 0003_remove_sale_payment_method.py
        │   └── 0004_cataloglot.py
        └── templates/clerk/
            ├── base.html              # Layout, CSS, inline JavaScript
            ├── event_list.html        # List/create/delete events
            ├── event_detail.html      # Workspace, sale entry, ledgers
            ├── event_tabs.html        # Shared navigation pills
            ├── catalog_lots.html      # Separate pre-load lots screen
            ├── bidder_lookup.html     # Bidder input + datalist
            ├── field.html             # Generic form field renderer
            ├── form.html              # Generic edit form page
            ├── checkout_all.html      # Buyer finder + print-all sheets
            ├── checkout_bidder.html   # One buyer's checkout sheet page
            ├── invoice.html           # Shared printed sheet markup
            └── confirm_delete.html    # Shared delete confirmation page
```

`__pycache__/` directories are generated by Python and can be ignored or safely
deleted while the server is stopped. `.secret_key` is generated locally and
gitignored; do not delete it if you want existing sessions to remain valid.

## 8. Component locations and responsibilities

| Component | Location | Responsibility |
| --- | --- | --- |
| Python runtime | system `python3` | Provides Python 3.12.3. |
| Virtual environment | `../.venv` | Isolates installed dependencies. |
| Django | `../.venv/lib/python3.12/site-packages/django` | Web framework and test runner. |
| openpyxl | `../.venv/lib/python3.12/site-packages/openpyxl` | Builds `.xlsx` exports. |
| Database | `auction_clerk/db.sqlite3` | Stores all events, lots, bidders, sales, and sessions. |
| Launcher | `auction_clerk/run.sh` | Sets directory and binds `0.0.0.0:8000`. |
| Settings | `clerk_site/settings.py` | Hosts, database, apps, middleware, timezone. |
| URL routing | `clerk_site/urls.py`, `clerk/urls.py` | Maps paths to views. |
| Business logic | `clerk/forms.py`, `clerk/views.py`, `clerk/models.py` | Validation, request flow, persistence. |
| UI | `clerk/templates/clerk/*.html` | Server-rendered pages and print styles. |
| JavaScript | inline in `base.html` | Print buttons and lot-number autofill. |
| Exports | `clerk/exports.py` | CSV/XLSX responses. |
| Tests | `clerk/tests.py` | Regression suite using a separate test DB. |
| Runtime log | stdout/stderr of the launching terminal | Redirect it to a log file if you want to keep server output. |

## 9. Data model

### Event

`clerk/models.py::Event`

- `title`, `sale_date`, `location`, `notes`, `created_at`.
- Related `bidders`, `catalog_lots`, and `sales` all cascade when the event is
  deleted.
- `total_sales` sums `line_total` across the event's sales.

### Bidder

`clerk/models.py::Bidder`

- Belongs to one `Event`.
- `number`, optional `name`, `phone`, `notes`, `created_at`.
- Unique constraint on `(event, number)`.
- `Bidder.next_number(event)` returns the highest number plus one.
- Sales use `on_delete=SET_NULL`, but the UI blocks deleting a bidder that still
  has sales.

### CatalogLot

`clerk/models.py::CatalogLot`

- Belongs to one `Event`.
- `number`, `description`, `quantity`, `notes`, `created_at`.
- Unique constraint on `(event, number)`.
- `is_sold` is computed by checking whether the event has a `Sale` with the same
  integer `lot` number. There is no direct foreign key from `Sale` to
  `CatalogLot`.
- `CatalogLot.next_number(event)` returns one more than the highest catalog or
  sold lot number.

### Sale

`clerk/models.py::Sale`

- Belongs to one `Event`.
- `lot` is nullable; `description`, `amount`, `quantity`, `bidder`, `notes`.
- `amount` is the unit price; `line_total = amount × quantity`.
- `bidder` is nullable so a lot can be recorded before the buyer is known.
- The form rejects duplicate lot numbers within an event, but the database does
  not have a unique constraint on `(event, lot)`.
- Payment method was deliberately removed; it is not stored or exported.

### Migration history

| Migration | Change |
| --- | --- |
| `0001_initial` | Original Event/Bidder/Sale schema, including payment method. |
| `0002_alter_sale_bidder` | Changed `Sale.bidder` to `SET_NULL`. |
| `0003_remove_sale_payment_method` | Removed payment method from the database. |
| `0004_cataloglot` | Added the pre-loaded lot model. |

## 10. URL map

Defined in `clerk/urls.py` and included at `/` by `clerk_site/urls.py`.

| Path | Name | View | Purpose |
| --- | --- | --- | --- |
| `/` | `event_list` | `event_list` | List/create entry point. |
| `/events/new/` | `event_new` | `event_form` | Create event. |
| `/events/<pk>/` | `event_detail` | `event_detail` | Workspace: sale entry, bidders, ledgers. |
| `/events/<pk>/lots/` | `catalog_lots` | `catalog_lots` | Separate pre-load lots screen. |
| `/events/<pk>/edit/` | `event_edit` | `event_form` | Edit event. |
| `/events/<pk>/delete/` | `event_delete` | `event_delete` | Confirm/delete event. |
| `/sales/<pk>/edit/` | `sale_edit` | `sale_form` | Edit sale. |
| `/sales/<pk>/delete/` | `sale_delete` | `sale_delete` | Confirm/delete sale. |
| `/bidders/<pk>/edit/` | `bidder_edit` | `bidder_form` | Edit bidder. |
| `/bidders/<pk>/delete/` | `bidder_delete` | `bidder_delete` | Confirm/delete bidder. |
| `/lots/<pk>/edit/` | `catalog_lot_edit` | `catalog_lot_form` | Edit pre-loaded lot. |
| `/lots/<pk>/delete/` | `catalog_lot_delete` | `catalog_lot_delete` | Confirm/delete pre-loaded lot. |
| `/events/<pk>/checkout/` | `checkout_all` | `checkout_all` | Buyer finder and print-all sheets. |
| `/events/<pk>/checkout/<bidder_pk>/` | `checkout_bidder` | `checkout_bidder` | One buyer's sheet. |
| `/events/<pk>/export.csv` | `export_csv` | `download_csv` | CSV download. |
| `/events/<pk>/export.xlsx` | `export_xlsx` | `download_xlsx` | XLSX download. |

There is no REST API. Pages use normal POST forms with CSRF tokens and GET links.

## 11. Request flow and UI details

1. `clerk_site/urls.py` includes `clerk.urls`.
2. A view in `clerk/views.py` loads objects from `clerk/models.py`.
3. `clerk/forms.py` validates POST data and resolves bidder/lot lookups.
4. The view renders a template with `render()` or redirects after success.
5. `base.html` provides layout, flash messages, print CSS, and inline JS.

Important implementation details:

- Bidder lookup is server-side and accepts `#number`, number, full label, full
  name, or partial name. Ambiguous matches are rejected.
- Checkout buyer lookup uses a normal GET form (`?buyer=...`) and redirects to the
  resolved buyer's sheet. It works without JavaScript.
- Lot-number autofill is client-side in `base.html` using the `lot-options`
  datalist and `data-description` / `data-quantity` attributes. The server also
  fills blank description/quantity from the pre-loaded lot.
- A blank sale lot uses `Sale.next_lot(event)`: first unsold pre-loaded number,
  otherwise the highest used number plus one.
- Flash messages use Django's session framework.
- Print CSS hides `.no-print`, `.topbar`, `.tabs`, `.messages`, and `.footer`.

## 12. Exports

`clerk/exports.py` creates downloads directly in memory.

### CSV

- Content type: `text/csv; charset=utf-8-sig` (Excel-friendly BOM).
- Columns: `Lot`, `Description`, `Amount`, `Bidder #`, `Bidder Name`,
  `Quantity`, `Total`, `Notes`.
- Text beginning with `=`, `+`, `-`, `@`, tab, CR, or LF is prefixed with `'`
  so spreadsheets treat it as text.

### XLSX

Sheets:

1. `Sales` — description, amount, bidder #, quantity, total, notes.
2. `Sales with names` — description, bidder name, amount, quantity, total,
   notes.
3. `Bidders` — bidder #, name, phone, notes, total.
4. `Lots` — lot #, description, quantity, Sold/Available status, notes.
5. One sheet per bidder, named with the bidder number, with quantity,
   description, amount, total, and a bold total row.

Styling uses openpyxl: frozen header row, colored headers, column widths, and
currency formatting. Cells that openpyxl would interpret as formulas or errors
are forced to string type.

Filenames are sanitized from the event title and ISO sale date.

## 13. Tests and maintenance

Run the full suite:

```bash
cd auction_clerk
../.venv/bin/python3 manage.py test clerk
```

Django creates a **separate test database**, so live auction data is not changed.
The suite covers event setup/edit/delete, bidder numbering and lookup, lot
pre-loading, sale entry validation, sale edits/deletes, checkout scoping, export
contents, and regression cases for previous crashes.

Additional checks:

```bash
../.venv/bin/python3 manage.py check
../.venv/bin/python3 manage.py makemigrations --check --dry-run
```

Both should report no issues. If `makemigrations --check` reports changes, either
generate and apply the new migration intentionally, or revert the model edit.

To inspect live data safely, use the shell in read-only mode first:

```bash
../.venv/bin/python3 manage.py shell
```

```python
from clerk.models import Event, Bidder, CatalogLot, Sale
list(Event.objects.values_list("id", "title"))
Sale.objects.count()
```

Writes from the shell affect live data immediately.

## 14. Backup and restore

### Backup

Stop the server first for a consistent copy. These commands assume you are in the
parent directory that contains `auction_clerk/`:

```bash
pkill -f "manage.py runserver 0.0.0.0:8000"
cp -a auction_clerk/db.sqlite3 /path/to/backup/
```

If files named `db.sqlite3-wal` or `db.sqlite3-shm` exist, copy them too. They are
part of SQLite's active state.

### Restore

```bash
pkill -f "manage.py runserver 0.0.0.0:8000"
cp -a /path/to/backup/db.sqlite3 auction_clerk/db.sqlite3
cd auction_clerk && ./run.sh
```

Restore the `-wal`/`-shm` companions as well if they were backed up.

Do not delete `db.sqlite3` unless you intentionally want to start over. There is
no application-level undo for deleted events, sales, bidders, or lots.

## 15. Troubleshooting

### First checks

```bash
cd auction_clerk
../.venv/bin/python3 manage.py check
ps -ef | grep '[m]anage.py runserver'
ss -ltnp | grep ':8000'
curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:8000/
```

Server output goes to the launching terminal. If you redirect it to a log file,
inspect that file instead.

### Symptom table

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Page will not open on another device | Wrong IP, server stopped, firewall, wrong port. | Run `hostname -I`, check `ss -ltnp`, allow the port, and use `http://<ip>:8000`. |
| `Address already in use` | Another process owns port 8000. | Stop the old server or change the port in `run.sh`. |
| `Connection refused` on localhost | Server not running or bound to a different port. | Start `./run.sh`; check `ss -ltnp`. |
| HTTP 400 DisallowedHost | `ALLOWED_HOSTS` was changed. | Add the hostname/IP or restore `["*"]` for LAN use. |
| CSRF verification failed | Cross-origin/HTTPS proxy mismatch or stale cookies. | Use the documented HTTP URL, clear cookies, or add the proxy origin to `CSRF_TRUSTED_ORIGINS`. |
| `ModuleNotFoundError: django` / `openpyxl` | Wrong interpreter or missing venv. | Use `../.venv/bin/python3`; reinstall with the pinned versions. |
| `no such table` | Migrations not applied. | Run `manage.py migrate`. |
| Template does not exist | Template moved/renamed or `APP_DIRS` changed. | Restore `clerk/templates/clerk/` and `APP_DIRS=True`. |
| Changes to Python code not appearing | Auto-reload missed the change. | Restart the server. |
| Database is locked | Two servers/processes writing, or external tool holding a transaction. | Stop duplicate processes; SQLite has a 20-second timeout. |
| Data missing after restart | Wrong database file used, or `db.sqlite3` was deleted/replaced. | Check `DATABASES` in settings and restore a backup. |
| Lot autofill does not work | Lot number not pre-loaded, mismatch, or stale browser page. | Check the **Pre-load lots** screen and hard-refresh the browser. |
| "Several bidders match" | Duplicate names. | Enter the bidder number with `#`. |
| Checkout sheet missing | Bidder has no recorded sales. | Record sales for that bidder or choose another buyer. |
| Export is blank | Wrong event selected or no sales recorded. | Open the intended event and verify its ledger. |
| CSV/XLSX opens with odd formula text | Security escaping intentionally prefixes formula-like text with `'`. | Expected behavior; remove the leading `'` manually if you want a formula. |
| Dates appear one day off | `TIME_ZONE = "UTC"`. | Change `TIME_ZONE` to the local zone in `settings.py` and restart. |
| Permission denied starting server | `run.sh` not executable or DB not writable. | `chmod +x run.sh`; ensure the server user owns the project files. |
| Deleted data needs recovery | No app-level undo. | Stop server and restore the backed-up `db.sqlite3`. |

## 16. Known limitations

- Django's development server is used; this is not a production-grade web
  server.
- `DEBUG=True`, `ALLOWED_HOSTS=["*"]`, and no authentication mean the app must
  stay on a trusted LAN.
- SQLite is adequate for a single clerk/small team but not heavy concurrent
  writes.
- No automatic startup after reboot is configured.
- Event deletion permanently removes all related data; only backups can restore
  it.
- Pre-loaded lots are linked to sales by matching lot numbers, not by a database
  foreign key. Changing a sale's lot number changes which pre-loaded lot appears
  sold.
- Payment method is intentionally not stored. Checkout sheets do not include
  "Received by" or "Date" lines.
- Any original spreadsheet files you keep outside this repository are reference
  material only; the app does not read or overwrite them.
