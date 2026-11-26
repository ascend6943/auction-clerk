import re

from django import forms

from .models import Bidder, CatalogLot, Event, Sale


def find_bidder(bidders, text):
    value = text.strip().casefold()
    plain = value.removeprefix("#").strip()
    if not plain:
        raise forms.ValidationError("Enter a bidder number or name.")
    if re.fullmatch(r"\d+", plain):
        matches = [bidder for bidder in bidders if str(bidder.number) == plain.lstrip("0")]
    else:
        matches = [bidder for bidder in bidders if str(bidder).casefold() == value]
        if not matches:
            matches = [bidder for bidder in bidders if bidder.name.casefold() == value]
        if not matches:
            matches = [bidder for bidder in bidders if value in bidder.name.casefold()]
    if len(matches) > 1:
        raise forms.ValidationError("Several bidders match. Choose a suggestion or enter the bidder number.")
    if not matches:
        raise forms.ValidationError("No bidder found for %(query)s.", params={"query": text})
    return matches[0]


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "sale_date", "location", "notes"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Martin Family Sale 2026"}),
            "sale_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "location": forms.TextInput(attrs={"placeholder": "Optional"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class BidderForm(forms.ModelForm):
    number = forms.IntegerField(
        required=False,
        min_value=1,
        label="Bidder #",
        help_text="Leave blank to assign the next available number.",
    )

    class Meta:
        model = Bidder
        fields = ["number", "name", "phone", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Optional"}),
            "phone": forms.TextInput(attrs={"placeholder": "Optional"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event or (self.instance.event if self.instance.pk else None)
        if self.instance.pk:
            self.fields["number"].initial = self.instance.number

    def clean_number(self):
        number = self.cleaned_data.get("number")
        if number and self.event:
            duplicate = Bidder.objects.filter(event=self.event, number=number)
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise forms.ValidationError(
                    f"Bidder #{number} is already registered for this sale."
                )
        return number

    def save(self, commit=True):
        bidder = super().save(commit=False)
        if self.event:
            bidder.event = self.event
        if not bidder.number:
            bidder.number = Bidder.next_number(self.event)
        if commit:
            bidder.save()
        return bidder


class CatalogLotForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1, initial=1)
    number = forms.IntegerField(
        required=False,
        min_value=1,
        label="Lot #",
        help_text="Leave blank to assign the next available number.",
    )

    class Meta:
        model = CatalogLot
        fields = ["number", "description", "quantity", "notes"]
        widgets = {
            "description": forms.TextInput(
                attrs={"placeholder": "Item description", "autocomplete": "off"}
            ),
            "quantity": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event or (self.instance.event if self.instance.pk else None)
        if self.instance.pk:
            self.fields["number"].initial = self.instance.number
            if self.instance.is_sold:
                self.fields["number"].disabled = True
                self.fields["number"].help_text = (
                    "This lot has a recorded sale, so its number cannot be changed."
                )

    def clean_number(self):
        number = self.cleaned_data.get("number")
        if number and self.event:
            if number != self.instance.number and self.event.sales.filter(lot=number).exists():
                raise forms.ValidationError(f"Lot #{number} already has a recorded sale.")
            duplicate = CatalogLot.objects.filter(event=self.event, number=number)
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise forms.ValidationError(
                    f"Lot #{number} is already pre-loaded for this sale."
                )
        return number

    def save(self, commit=True):
        lot = super().save(commit=False)
        if self.event:
            lot.event = self.event
        if not lot.number:
            lot.number = CatalogLot.next_number(self.event)
        if commit:
            lot.save()
        return lot


class SaleForm(forms.ModelForm):
    quantity = forms.IntegerField(required=False, min_value=1)
    lot = forms.IntegerField(
        required=False,
        min_value=1,
        label="Lot #",
        help_text="Type a pre-loaded lot number to fill in the item. Blank = next unsold lot.",
        widget=forms.TextInput(
            attrs={
                "list": "lot-options",
                "data-lot-lookup": "1",
                "autocomplete": "off",
                "inputmode": "numeric",
                "placeholder": "Lot #",
            }
        ),
    )
    bidder_lookup = forms.CharField(
        required=False,
        label="Bidder",
        help_text="Type a bidder # or name to find the buyer. Blank = unassigned.",
        widget=forms.TextInput(
            attrs={
                "list": "bidder-options",
                "autocomplete": "off",
                "placeholder": "Type # or name",
            }
        ),
    )

    class Meta:
        model = Sale
        fields = [
            "lot",
            "description",
            "amount",
            "quantity",
            "notes",
        ]
        widgets = {
            "description": forms.TextInput(
                attrs={"placeholder": "What was sold?", "autocomplete": "off"}
            ),
            "amount": forms.NumberInput(
                attrs={"min": "0", "step": "0.01", "placeholder": "0.00"}
            ),
            "quantity": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event or (self.instance.event if self.instance.pk else None)
        self.bidder_queryset = (
            Bidder.objects.filter(event=self.event).order_by("number")
            if self.event
            else Bidder.objects.none()
        )
        # These can be filled from a pre-loaded lot during clean().
        self.fields["description"].required = False
        if not self.instance.pk:
            self.initial.pop("quantity", None)
        self.bidder_choices = [
            {"id": bidder.pk, "number": bidder.number, "label": str(bidder)}
            for bidder in self.bidder_queryset
        ]
        self.catalog_queryset = (
            CatalogLot.objects.filter(event=self.event).order_by("number")
            if self.event
            else CatalogLot.objects.none()
        )
        self.catalog_choices = [
            {
                "number": lot.number,
                "description": lot.description,
                "quantity": lot.quantity,
            }
            for lot in self.catalog_queryset
        ]
        if self.instance.pk:
            self.fields["lot"].initial = self.instance.lot
            if self.instance.bidder_id:
                self.fields["bidder_lookup"].initial = str(self.instance.bidder)

    def clean_lot(self):
        lot = self.cleaned_data.get("lot")
        if lot is None and self.event:
            lot = self.instance.lot or Sale.next_lot(self.event)
        if lot and self.event:
            duplicate = Sale.objects.filter(event=self.event, lot=lot)
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise forms.ValidationError(f"Lot #{lot} is already used in this sale.")
        return lot

    def clean(self):
        cleaned = super().clean()

        lot = cleaned.get("lot")
        catalog_lot = None
        if lot and self.event:
            catalog_lot = self.catalog_queryset.filter(number=lot).first()
            if catalog_lot and cleaned.get("description") == "":
                cleaned["description"] = catalog_lot.description
        if cleaned.get("description") == "":
            self.add_error("description", "Enter an item description or choose a pre-loaded lot.")

        if "quantity" in cleaned and cleaned["quantity"] is None:
            cleaned["quantity"] = catalog_lot.quantity if catalog_lot else 1

        lookup = cleaned.get("bidder_lookup") or ""
        if not lookup.strip():
            cleaned["bidder"] = None
            return cleaned

        try:
            cleaned["bidder"] = find_bidder(self.bidder_queryset, lookup)
        except forms.ValidationError as error:
            self.add_error("bidder_lookup", error)
        return cleaned

    def save(self, commit=True):
        sale = super().save(commit=False)
        if self.event:
            sale.event = self.event
        sale.bidder = self.cleaned_data["bidder"]
        if commit:
            sale.save()
        return sale
