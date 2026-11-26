import csv
import re

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

MONEY_FORMAT = '"$"#,##0.00'


def safe_filename(event):
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", event.title).strip("_") or "sale"
    return f"{base}_{event.sale_date.isoformat()}"


def _csv_text(value):
    # Keep user-entered text literal when a spreadsheet opens the CSV.
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def export_csv(event):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = (
        f'attachment; filename="{safe_filename(event)}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(
        [
            "Lot",
            "Description",
            "Amount",
            "Bidder #",
            "Bidder Name",
            "Quantity",
            "Total",
            "Notes",
        ]
    )
    for sale in event.sales.select_related("bidder").all():
        writer.writerow(
            [
                sale.lot or "",
                _csv_text(sale.description),
                f"{sale.amount:.2f}",
                sale.bidder.number if sale.bidder else "",
                _csv_text(sale.bidder.name) if sale.bidder else "",
                sale.quantity,
                f"{sale.line_total:.2f}",
                _csv_text(sale.notes),
            ]
        )
    return response


def _style_sheet(ws, headers, widths=None):
    ws.append(headers)
    header_fill = PatternFill("solid", fgColor="1F3552")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"
    widths = widths or [18] * len(headers)
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width


def _format_money(ws, columns):
    for column in columns:
        for cell in ws[column][1:]:
            cell.number_format = MONEY_FORMAT


def export_xlsx(event):
    """Export in the shape of the original clerking spreadsheet."""
    wb = Workbook()

    sales_ws = wb.active
    sales_ws.title = "Sales"
    _style_sheet(
        sales_ws,
        ["Description", "Amount", "Bidder #", "Quantity", "Total", "Notes"],
        widths=[38, 12, 10, 11, 12, 30],
    )
    for sale in event.sales.select_related("bidder").all():
        sales_ws.append(
            [
                sale.description,
                float(sale.amount),
                sale.bidder.number if sale.bidder else None,
                sale.quantity,
                float(sale.line_total),
                sale.notes,
            ]
        )
    _format_money(sales_ws, ("B", "E"))

    named_ws = wb.create_sheet("Sales with names")
    _style_sheet(
        named_ws,
        ["Description", "Bidder", "Amount", "Quantity", "Total", "Notes"],
        widths=[38, 24, 12, 11, 12, 30],
    )
    for sale in event.sales.select_related("bidder").all():
        named_ws.append(
            [
                sale.description,
                sale.bidder.name if sale.bidder else "(no bidder)",
                float(sale.amount),
                sale.quantity,
                float(sale.line_total),
                sale.notes,
            ]
        )
    _format_money(named_ws, ("C", "E"))

    bidders_ws = wb.create_sheet("Bidders")
    _style_sheet(
        bidders_ws,
        ["Bidder #", "Name", "Phone", "Notes", "Total"],
        widths=[12, 26, 18, 30, 14],
    )
    for bidder in event.bidders.prefetch_related("sales").all():
        bidders_ws.append(
            [
                bidder.number,
                bidder.name,
                bidder.phone,
                bidder.notes,
                float(bidder.total),
            ]
        )
    _format_money(bidders_ws, ("E",))

    lots_ws = wb.create_sheet("Lots")
    _style_sheet(
        lots_ws,
        ["Lot #", "Description", "Quantity", "Status", "Notes"],
        widths=[10, 40, 11, 14, 30],
    )
    sold_numbers = {
        number
        for number in event.sales.values_list("lot", flat=True)
        if number is not None
    }
    for lot in event.catalog_lots.all():
        lots_ws.append(
            [
                lot.number,
                lot.description,
                lot.quantity,
                "Sold" if lot.number in sold_numbers else "Available",
                lot.notes,
            ]
        )

    # One invoice-style sheet per bidder, matching the numbered sheets in the workbook.
    for bidder in event.bidders.prefetch_related("sales").all():
        sheet = wb.create_sheet(str(bidder.number))
        _style_sheet(
            sheet,
            ["Quantity", "Description", "Amount", "Total"],
            widths=[11, 42, 14, 14],
        )
        for sale in bidder.sales.all():
            sheet.append(
                [
                    sale.quantity,
                    sale.description,
                    float(sale.amount),
                    float(sale.line_total),
                ]
            )
        sheet.append([None, "TOTAL", None, float(bidder.total)])
        _format_money(sheet, ("C", "D"))
        total_row = sheet.max_row
        for cell in sheet[total_row]:
            cell.font = Font(bold=True)

    # This export contains values only; openpyxl otherwise treats text starting
    # with '=' as a formula and some literal strings as spreadsheet errors.
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.data_type in ("f", "e"):
                    cell.data_type = "s"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{safe_filename(event)}.xlsx"'
    )
    wb.save(response)
    return response
