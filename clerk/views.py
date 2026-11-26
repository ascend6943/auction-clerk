from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .exports import export_csv, export_xlsx
from .forms import BidderForm, CatalogLotForm, EventForm, SaleForm, find_bidder
from .models import Bidder, CatalogLot, Event, Sale


def event_list(request):
    events = Event.objects.all()
    return render(request, "clerk/event_list.html", {"events": events})


def event_form(request, pk=None):
    event = get_object_or_404(Event, pk=pk) if pk else None
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            saved = form.save()
            messages.success(
                request,
                "Sale updated." if event else f"Sale '{saved.title}' created.",
            )
            return redirect("event_detail", pk=saved.pk)
    else:
        form = EventForm(instance=event)
    return render(
        request,
        "clerk/form.html",
        {
            "form": form,
            "title": "Edit sale" if event else "New sale",
            "submit_label": "Save sale",
            "cancel_url": "event_detail" if event else "event_list",
            "cancel_args": [event.pk] if event else [],
            "event": event,
        },
    )


def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        title = event.title
        event.delete()
        messages.success(request, f"Sale '{title}' deleted.")
        return redirect("event_list")
    return render(
        request,
        "clerk/confirm_delete.html",
        {
            "object": event,
            "description": (
                f"sale '{event.title}' and all of its recorded sales, bidders, "
                "and pre-loaded lots"
            ),
            "cancel_url": "event_detail",
            "cancel_args": [event.pk],
        },
    )


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    action = request.POST.get("action") if request.method == "POST" else None

    sale_form = SaleForm(request.POST if action == "add_sale" else None, event=event)
    bidder_form = BidderForm(
        request.POST if action == "add_bidder" else None, event=event
    )

    if action == "add_sale" and sale_form.is_valid():
        sale = sale_form.save()
        messages.success(request, f"Lot {sale.lot} recorded.")
        return redirect("event_detail", pk=event.pk)
    if action == "add_bidder" and bidder_form.is_valid():
        bidder = bidder_form.save()
        messages.success(request, f"Bidder #{bidder.number} added.")
        return redirect("event_detail", pk=event.pk)

    sales = list(event.sales.select_related("bidder").all())
    bidders = list(event.bidders.prefetch_related("sales").all())
    rows = []
    for bidder in bidders:
        rows.append(
            {
                "bidder": bidder,
                "total": sum((sale.line_total for sale in bidder.sales.all()), 0),
                "count": len(bidder.sales.all()),
            }
        )

    return render(
        request,
        "clerk/event_detail.html",
        {
            "event": event,
            "sales": sales,
            "sale_form": sale_form,
            "bidder_form": bidder_form,
            "bidder_rows": rows,
            "total_sales": sum((sale.line_total for sale in sales), 0),
            "unassigned_count": sum(1 for sale in sales if sale.bidder is None),
        },
    )


def sale_form(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    event = sale.event
    if request.method == "POST":
        form = SaleForm(request.POST, instance=sale, event=event)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f"Lot {saved.lot} updated.")
            return redirect("event_detail", pk=event.pk)
    else:
        form = SaleForm(instance=sale, event=event)
    return render(
        request,
        "clerk/form.html",
        {
            "form": form,
            "title": f"Edit lot {sale.lot or ''}".strip(),
            "submit_label": "Save lot",
            "cancel_url": "event_detail",
            "cancel_args": [event.pk],
            "event": event,
        },
    )


def sale_delete(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    event = sale.event
    if request.method == "POST":
        sale.delete()
        messages.success(request, "Lot deleted.")
        return redirect("event_detail", pk=event.pk)
    return render(
        request,
        "clerk/confirm_delete.html",
        {
            "object": sale,
            "description": f"lot {sale.lot} ({sale.description})",
            "cancel_url": "event_detail",
            "cancel_args": [event.pk],
        },
    )


def bidder_form(request, pk):
    bidder = get_object_or_404(Bidder, pk=pk)
    event = bidder.event
    if request.method == "POST":
        form = BidderForm(request.POST, instance=bidder, event=event)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f"Bidder #{saved.number} updated.")
            return redirect("event_detail", pk=event.pk)
    else:
        form = BidderForm(instance=bidder, event=event)
    return render(
        request,
        "clerk/form.html",
        {
            "form": form,
            "title": f"Edit bidder #{bidder.number}",
            "submit_label": "Save bidder",
            "cancel_url": "event_detail",
            "cancel_args": [event.pk],
            "event": event,
        },
    )


def bidder_delete(request, pk):
    bidder = get_object_or_404(Bidder, pk=pk)
    event = bidder.event
    if bidder.sales.exists():
        messages.error(
            request,
            f"Bidder #{bidder.number} has recorded lots. Reassign or delete those "
            "lots before removing the bidder.",
        )
        return redirect("event_detail", pk=event.pk)
    if request.method == "POST":
        bidder.delete()
        messages.success(request, f"Bidder #{bidder.number} removed.")
        return redirect("event_detail", pk=event.pk)
    return render(
        request,
        "clerk/confirm_delete.html",
        {
            "object": bidder,
            "description": f"bidder #{bidder.number}",
            "cancel_url": "event_detail",
            "cancel_args": [event.pk],
        },
    )


def catalog_lots(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        form = CatalogLotForm(request.POST, event=event)
        if form.is_valid():
            lot = form.save()
            messages.success(request, f"Lot {lot.number} pre-loaded.")
            return redirect("catalog_lots", pk=event.pk)
    else:
        form = CatalogLotForm(event=event)

    sold_numbers = {
        number
        for number in event.sales.values_list("lot", flat=True)
        if number is not None
    }
    rows = [
        {"lot": lot, "sold": lot.number in sold_numbers}
        for lot in event.catalog_lots.all()
    ]
    return render(
        request,
        "clerk/catalog_lots.html",
        {"event": event, "form": form, "rows": rows},
    )


def catalog_lot_form(request, pk):
    lot = get_object_or_404(CatalogLot, pk=pk)
    event = lot.event
    if request.method == "POST":
        form = CatalogLotForm(request.POST, instance=lot, event=event)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f"Lot {saved.number} updated.")
            return redirect("catalog_lots", pk=event.pk)
    else:
        form = CatalogLotForm(instance=lot, event=event)
    return render(
        request,
        "clerk/form.html",
        {
            "form": form,
            "title": f"Edit lot {lot.number}",
            "submit_label": "Save lot",
            "cancel_url": "catalog_lots",
            "cancel_args": [event.pk],
            "event": None,
        },
    )


def catalog_lot_delete(request, pk):
    lot = get_object_or_404(CatalogLot, pk=pk)
    event = lot.event
    if Sale.objects.filter(event=event, lot=lot.number).exists():
        messages.error(
            request,
            f"Lot {lot.number} has a recorded sale. Delete or change that sale first.",
        )
        return redirect("catalog_lots", pk=event.pk)
    if request.method == "POST":
        lot.delete()
        messages.success(request, f"Lot {lot.number} removed.")
        return redirect("catalog_lots", pk=event.pk)
    return render(
        request,
        "clerk/confirm_delete.html",
        {
            "object": lot,
            "description": f"lot {lot.number} ({lot.description})",
            "cancel_url": "catalog_lots",
            "cancel_args": [event.pk],
        },
    )


def _checkout_rows(event):
    rows = []
    for bidder in event.bidders.prefetch_related("sales").all():
        sales = list(bidder.sales.all())
        if not sales:
            continue
        rows.append(
            {
                "bidder": bidder,
                "sales": sales,
                "total": sum((sale.line_total for sale in sales), 0),
            }
        )
    return rows


def checkout_all(request, pk):
    event = get_object_or_404(Event, pk=pk)
    bidders = list(event.bidders.all())
    query = request.GET.get("buyer")
    lookup_error = None
    if query is not None:
        try:
            bidder = find_bidder(bidders, query)
        except forms.ValidationError as error:
            lookup_error = error.messages[0]
        else:
            return redirect("checkout_bidder", pk=event.pk, bidder_pk=bidder.pk)
    return render(
        request,
        "clerk/checkout_all.html",
        {
            "event": event,
            "rows": _checkout_rows(event),
            "bidders": bidders,
            "query": query or "",
            "lookup_error": lookup_error,
        },
    )


def checkout_bidder(request, pk, bidder_pk):
    event = get_object_or_404(Event, pk=pk)
    bidder = get_object_or_404(Bidder, pk=bidder_pk, event=event)
    sales = list(bidder.sales.all())
    return render(
        request,
        "clerk/checkout_bidder.html",
        {
            "event": event,
            "bidder": bidder,
            "sales": sales,
            "total": sum((sale.line_total for sale in sales), 0),
        },
    )


def download_csv(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return export_csv(event)


def download_xlsx(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return export_xlsx(event)
