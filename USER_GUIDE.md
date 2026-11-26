# Auction Clerk — User Guide

Auction Clerk is a small web app for recording an auction sale on a local network.
It keeps each sale event separate, with its own bidders, pre-loaded lots, sales
ledger, checkout sheets, and exports.

There is **no login screen** and no sample data. Use it only on a trusted LAN.
Data is saved in the app's database as you work; stopping the server does not
delete it.

## Opening the app

On the computer running the app:

```text
http://localhost:8000
```

From another device on the same LAN:

```text
http://<computer-ip>:8000
```

If you do not know the computer's LAN address, ask the person who started the
server. On Linux, `hostname -I` shows it. The address is assigned by DHCP and
can change.

## The main screens

After you open an event, the row of pills across the top gives you:

| Pill | Purpose |
| --- | --- |
| **Workspace** | Record sales, add bidders, and view the sales ledger. |
| **Pre-load lots** | Enter item descriptions and lot numbers before the sale. |
| **Checkout sheets** | Find or print buyer checkout sheets. |
| **Sale details** | Edit the event title, date, location, and notes. |
| **Export CSV** / **Export XLSX** | Download the event's data. |
| **All sales** | Return to the list of sale events. |
| **Delete sale** | Remove the event after confirmation. |

## 1. Create or open a sale event

From the **Sale events** list:

- Click **+ New sale event** to create one.
- Enter a title, sale date, optional location, and optional notes.
- Click **Save sale**.

Each event is independent. Bidder numbers, lot numbers, and totals start fresh
for each event.

From the same list you can **Edit** an event or **Delete** it. Deleting an event
asks for confirmation and removes that event's recorded sales, bidders, and
pre-loaded lots. Other events are unaffected.

## 2. Before the sale: pre-load lots

Use **Pre-load lots → Add an item** to enter items ahead of time.

| Field | What to enter |
| --- | --- |
| **Lot #** | Optional. Leave blank to assign the next available number. |
| **Description** | The item description. |
| **Quantity** | Defaults to 1. Must be at least 1. |
| **Notes** | Optional. |

The **Pre-loaded items** table shows each item as **Available** or **Sold**.

- An item becomes **Sold** when a sale with that lot number is recorded.
- You can **Edit** a pre-loaded lot. Once it is sold, its number is locked so the
  sale record stays linked, but the description, quantity, and notes can change.
- You can **Delete** an unsold lot. A sold lot cannot be deleted until its sale
  is changed or deleted.

Pre-loading is optional. You can still type an item description directly while
recording a sale.

## 3. Add bidders

On the **Workspace**, use **Add a bidder**.

| Field | What to enter |
| --- | --- |
| **Bidder #** | Optional. Leave blank to assign the next number. |
| **Name** | Optional; can be filled in later. |
| **Phone** | Optional. |
| **Notes** | Optional. |

Bidder numbers start at **1** for each event. Reusing a number already registered
for that event is rejected. Names can be left blank if you only know the bidder
number at the time.

The **Bidders** table shows each bidder's number, name, phone, number of lots, and
total. Use **Edit** to fill in missing details later. **Delete** is available only
when that bidder has no recorded sales; reassign or delete the sales first.

## 4. Record a sale

On the **Workspace**, use **Record a sale**.

| Field | What to enter |
| --- | --- |
| **Lot #** | Type a pre-loaded lot number, or leave blank. |
| **Description** | Filled from the pre-loaded lot, or type it yourself. |
| **Amount** | Unit price for this sale. |
| **Qty** | Quantity; defaults to 1. |
| **Bidder** | Type a bidder number or name, or leave blank. |
| **Notes** | Optional. |

### Using a pre-loaded lot

Type the lot number in **Lot #**. The browser suggests pre-loaded numbers, and
the description and quantity fill in automatically. Enter the **amount** and
**buyer** at the time of the sale.

If you leave **Lot #** blank, the app uses the next unsold pre-loaded lot. If all
pre-loaded lots are sold, it assigns the next unused number.

### Choosing the buyer

The **Bidder** field accepts:

- `7` or `#7`
- A full name, such as `Ann Smith`
- Part of a name, such as `ann`
- The full suggestion text, such as `#7 - Ann Smith`

If two bidders have similar names, the app asks you to use the bidder number.
Leaving the field blank records the lot as **Unassigned**; you can edit it later.

### Totals and corrections

- The ledger's **Total** is `Amount × Qty`.
- A lot number already used in this sale is rejected. Edit or delete the existing
  sale before reusing the number.
- Click **Record sale** to save immediately. There is no separate Save button on
  this form.
- Use **Edit** or **Delete** in the **Sales ledger** to correct a sale.

## 5. Checkout sheets

Open **Checkout sheets** from the event navigation.

### One buyer

In **Find one buyer**, type a bidder number or name and click **Open checkout
sheet**. The app opens that buyer's sheet directly.

### All buyers

Click **Print all** to print one sheet per bidder who has recorded lots. Bidders
with no sales are not printed.

A checkout sheet shows:

- Event title and sale date
- Bidder number, name, and phone
- Each lot, description, quantity, unit price, and line total
- **Total due**
- Bidder notes, if any

The print button uses your browser's print dialog. Navigation and buttons are
hidden when printing. Payment method is intentionally not shown or recorded here;
it is decided separately at the time the sheet is used.

## 6. Exports

Use **Export CSV** or **Export XLSX** from the event navigation.

Downloaded filenames are based on the event title and sale date, with unsafe
characters replaced by underscores.

### CSV columns

```text
Lot, Description, Amount, Bidder #, Bidder Name, Quantity, Total, Notes
```

### XLSX sheets

| Sheet | Contents |
| --- | --- |
| `Sales` | Recorded sales with bidder numbers. |
| `Sales with names` | Recorded sales with bidder names. |
| `Bidders` | Bidder numbers, contact details, notes, and totals. |
| `Lots` | Pre-loaded lots and their Sold/Available status. |
| `<number>` | One invoice-style sheet per bidder. |

Text that looks like a spreadsheet formula is exported as literal text so it is
not evaluated when the file is opened.

## 7. Typical workflow

### Before the sale

1. Create the sale event.
2. Pre-load the item list and lot numbers.
3. Register bidders as they receive numbers. Names and phone numbers can be added
   later.

### During the sale

1. Type the lot number in **Record a sale**.
2. Confirm the description and quantity.
3. Enter the winning amount and bidder.
4. Click **Record sale**.

### After the sale

1. Fill in any missing bidder names or phone numbers.
2. Open **Checkout sheets** and print one sheet per buyer.
3. Download CSV or XLSX records for your files.
4. Make a backup of the database if you want to keep a restore point.

## 8. Important rules and gotchas

- Everything is **per event**. A bidder number from one event does not exist in
  another event.
- Deletes ask for confirmation and cannot be undone from the app. Keep database
  backups if the data matters.
- You cannot delete a bidder or pre-loaded lot that still has recorded sales.
  Change or delete the sale first.
- Deleting a sale makes its pre-loaded lot **Available** again.
- Closing the browser, stopping the server, or restarting the computer does not
  delete data. Only deleting or replacing the database file does.
- This app has no user accounts. Do not expose it to the public internet.

## 9. Common user issues

| Symptom | What to do |
| --- | --- |
| The page will not open from another device | Confirm the server is running, use the right LAN address, and check the firewall/port. |
| "No bidder found" | Register the bidder for this event, or check the number/name spelling. |
| "Several bidders match" | Use the bidder number, such as `#7`. |
| "Lot # is already used" | Edit or delete the existing sale with that lot number. |
| Lot details did not fill in | Make sure the lot is pre-loaded for this event and the number matches exactly. You can still type the description and quantity manually. |
| A bidder cannot be deleted | Reassign or delete that bidder's recorded sales first. |
| A checkout sheet is missing | Only bidders with recorded sales are shown. |
| Dates look one day off | The app stores dates in UTC; check the computer/region and the configuration if this happens near midnight. |
