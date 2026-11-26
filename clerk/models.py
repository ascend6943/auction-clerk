from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Event(models.Model):
    """One sale event, e.g. a family auction on a given date."""

    title = models.CharField(max_length=150)
    sale_date = models.DateField(default=timezone.localdate)
    location = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sale_date", "-id"]

    def __str__(self):
        return self.title

    @property
    def total_sales(self):
        return sum((sale.line_total for sale in self.sales.all()), Decimal("0.00"))


class Bidder(models.Model):
    """A numbered buyer within one event. Numbers start at 1 for each event."""

    event = models.ForeignKey(Event, related_name="bidders", on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=60, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "number"], name="unique_bidder_number_per_event"
            )
        ]

    def __str__(self):
        label = f"#{self.number}"
        return f"{label} - {self.name}" if self.name else label

    @property
    def total(self):
        return sum((sale.line_total for sale in self.sales.all()), Decimal("0.00"))

    @property
    def item_count(self):
        return sum(sale.quantity for sale in self.sales.all())

    @classmethod
    def next_number(cls, event):
        highest = cls.objects.filter(event=event).aggregate(
            highest=models.Max("number")
        )["highest"]
        return (highest or 0) + 1


class CatalogLot(models.Model):
    """An item prepared before the sale, with its lot number."""

    event = models.ForeignKey(Event, related_name="catalog_lots", on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    description = models.CharField(max_length=250)
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "number"], name="unique_catalog_lot_per_event"
            )
        ]

    def __str__(self):
        return f"Lot {self.number} - {self.description}"

    @property
    def is_sold(self):
        return self.event.sales.filter(lot=self.number).exists()

    @classmethod
    def next_number(cls, event):
        highest = cls.objects.filter(event=event).aggregate(
            highest=models.Max("number")
        )["highest"]
        highest_sold = event.sales.aggregate(highest=models.Max("lot"))["highest"]
        return max(highest or 0, highest_sold or 0) + 1


class Sale(models.Model):
    """A sold lot: description, unit price, quantity and winning bidder."""

    event = models.ForeignKey(Event, related_name="sales", on_delete=models.CASCADE)
    lot = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=250)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Price per item",
    )
    quantity = models.PositiveIntegerField(default=1)
    bidder = models.ForeignKey(
        Bidder,
        related_name="sales",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Leave blank if the buyer has not been entered yet.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["lot", "id"]

    def __str__(self):
        return f"Lot {self.lot or '-'} - {self.description}"

    @property
    def line_total(self):
        return self.amount * self.quantity

    @classmethod
    def next_lot(cls, event):
        used = set(
            value
            for value in cls.objects.filter(event=event).values_list("lot", flat=True)
            if value is not None
        )
        catalog_numbers = list(
            CatalogLot.objects.filter(event=event).order_by("number").values_list("number", flat=True)
        )
        for number in catalog_numbers:
            if number not in used:
                return number
        return max(used, default=0) + 1
