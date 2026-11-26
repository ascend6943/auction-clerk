import csv
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO

from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from .forms import BidderForm, CatalogLotForm, SaleForm
from .models import Bidder, CatalogLot, Event, Sale


class AutomaticLotNumberTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(title="Test auction")

    def record_sale(self, description="Lamp"):
        response = self.client.post(
            reverse("event_detail", args=[self.event.pk]),
            {"action": "add_sale", "description": description, "amount": "10.00"},
        )
        self.assertRedirects(response, reverse("event_detail", args=[self.event.pk]))
        return self.event.sales.latest("pk")

    def test_blank_number_with_no_preloaded_lots(self):
        self.assertEqual(self.record_sale().lot, 1)
        self.assertEqual(self.record_sale().lot, 2)

    def test_blank_number_after_last_preloaded_lot_is_sold(self):
        CatalogLot.objects.create(event=self.event, number=5, description="Chair")
        Sale.objects.create(event=self.event, lot=5, description="Chair", amount="8.00")

        self.assertEqual(self.record_sale().lot, 6)

    def test_blank_number_still_uses_next_unsold_preloaded_lot(self):
        CatalogLot.objects.create(
            event=self.event, number=4, description="Vase", quantity=2
        )

        sale = self.record_sale(description="")
        self.assertEqual((sale.lot, sale.description, sale.quantity), (4, "Vase", 2))


class AuctionWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = Event.objects.create(title="Spring auction")
        cls.other = Event.objects.create(title="Fall auction")
        cls.buyer = Bidder.objects.create(event=cls.event, number=7, name="Ann Smith")
        cls.outsider = Bidder.objects.create(event=cls.other, number=9, name="Pat")
        cls.workspace = reverse("event_detail", args=[cls.event.pk])
        cls.catalog = reverse("catalog_lots", args=[cls.event.pk])
        cls.checkout = reverse("checkout_all", args=[cls.event.pk])
        cls.invoice = reverse("checkout_bidder", args=[cls.event.pk, cls.buyer.pk])

    def record(self, **overrides):
        data = {
            "action": "add_sale", "lot": "12", "description": "Lamp",
            "amount": "12.55", "quantity": "2", "bidder_lookup": "#7",
        }
        return self.client.post(self.workspace, data | overrides)

    def test_create_and_edit_event(self):
        response = self.client.post(reverse("event_new"), {
            "title": "Barn auction", "sale_date": "2026-11-25", "location": "Barn",
        })
        event = Event.objects.get(title="Barn auction")
        self.assertRedirects(response, reverse("event_detail", args=[event.pk]))
        edit = reverse("event_edit", args=[event.pk])
        self.assertContains(self.client.get(edit), 'value="2026-11-25"')
        self.assertRedirects(self.client.post(edit, {
            "title": "Barn auction moved", "sale_date": "2026-12-01",
        }), reverse("event_detail", args=[event.pk]))
        event.refresh_from_db()
        self.assertEqual(event.sale_date, date(2026, 12, 1))

    def test_bidder_number_validation_and_event_scope(self):
        self.assertContains(self.client.post(self.workspace, {
            "action": "add_bidder", "number": "7", "name": "Duplicate",
        }), "already registered")
        self.assertRedirects(self.client.post(self.workspace, {
            "action": "add_bidder", "number": "", "name": "Next buyer",
        }), self.workspace)
        self.assertEqual(self.event.bidders.get(name="Next buyer").number, 8)
        self.assertRedirects(self.client.post(self.workspace, {
            "action": "add_bidder", "number": "9", "name": "Local buyer",
        }), self.workspace)
        self.assertEqual(self.other.bidders.get(number=9), self.outsider)

    def test_catalog_is_separate_and_prefills_sale(self):
        self.assertNotContains(self.client.get(self.workspace), "Pre-loaded items")
        self.assertContains(self.client.get(self.workspace), self.catalog)
        self.assertRedirects(self.client.post(self.catalog, {
            "number": "12", "description": "Vase", "quantity": "3",
        }), self.catalog)
        self.assertContains(self.client.get(self.workspace), 'data-description="Vase"')
        self.assertRedirects(self.record(description="", quantity="", bidder_lookup="ann sm"), self.workspace)
        sale = self.event.sales.get()
        self.assertEqual((sale.description, sale.quantity, sale.bidder), ("Vase", 3, self.buyer))
        self.assertEqual(sale.line_total, Decimal("37.65"))
        self.assertContains(self.client.get(self.catalog), "Sold")
        self.assertContains(self.record(), "already used")

    def test_catalog_cannot_reuse_sold_number(self):
        self.assertRedirects(self.record(), self.workspace)
        self.assertContains(self.client.post(self.catalog, {
            "number": "12", "description": "Unrelated lot", "quantity": "1",
        }), "already has a recorded sale")
        self.assertRedirects(self.client.post(self.catalog, {
            "number": "", "description": "New lot", "quantity": "1",
        }), self.catalog)
        self.assertEqual(self.event.catalog_lots.get().number, 13)

    def test_blank_lot_preserves_entered_quantity(self):
        CatalogLot.objects.create(event=self.event, number=4, description="Vase", quantity=8)
        self.assertRedirects(self.record(lot="", description="", quantity="2"), self.workspace)
        self.assertEqual(self.event.sales.get().quantity, 2)

    def test_invalid_sales_do_not_save(self):
        for overrides, error in [
            ({"description": ""}, "Enter an item description"),
            ({"quantity": "0"}, "greater than or equal to 1"),
            ({"amount": "-1"}, "greater than or equal to"),
            ({"bidder_lookup": "#9"}, "No bidder found"),
        ]:
            with self.subTest(overrides=overrides):
                self.assertContains(self.record(**overrides), error)
        self.assertFalse(self.event.sales.exists())

    def test_ambiguous_buyer_requires_a_choice_in_sale_and_checkout(self):
        Bidder.objects.create(event=self.event, number=8, name="Ann Smith")
        self.assertContains(self.record(bidder_lookup="Ann Smith"), "Several bidders match")
        self.assertFalse(self.event.sales.exists())
        self.assertContains(self.client.get(self.checkout, {"buyer": "Ann"}), "Several bidders match")
        self.assertRedirects(self.client.get(self.checkout, {"buyer": str(self.buyer)}), self.invoice)
        self.assertRedirects(self.record(bidder_lookup="007"), self.workspace)
        self.assertEqual(self.event.sales.get().bidder, self.buyer)

    def test_checkout_only_renders_buyers_lots(self):
        self.assertRedirects(self.record(), self.workspace)
        self.assertRedirects(self.record(lot="13", description="Unassigned chair", bidder_lookup=""), self.workspace)
        self.assertRedirects(self.client.get(self.checkout, {"buyer": "smith"}), self.invoice)
        self.assertContains(self.client.get(self.checkout, {"buyer": "Pat"}), "No bidder found")
        self.assertEqual(self.client.get(reverse("checkout_bidder", args=[
            self.event.pk, self.outsider.pk,
        ])).status_code, 404)
        invoice = self.client.get(self.invoice)
        self.assertContains(invoice, "Lamp")
        self.assertContains(invoice, "$25.10")
        self.assertNotContains(invoice, "Unassigned chair")
        self.assertNotContains(invoice, "Received by:")

    def test_edit_sale_can_unassign_buyer_and_keep_lot_number(self):
        self.assertRedirects(self.record(), self.workspace)
        sale = self.event.sales.get()
        self.assertRedirects(self.client.post(reverse("sale_edit", args=[sale.pk]), {
            "lot": "", "description": "Edited lamp", "amount": "8.00",
            "quantity": "3", "bidder_lookup": "",
        }), self.workspace)
        sale.refresh_from_db()
        self.assertEqual((sale.lot, sale.bidder, sale.line_total), (12, None, Decimal("24.00")))

    def test_catalog_and_bidder_deletion_protected_until_sale_removed(self):
        lot = CatalogLot.objects.create(event=self.event, number=12, description="Lamp")
        self.assertRedirects(self.record(), self.workspace)
        delete_bidder = reverse("bidder_delete", args=[self.buyer.pk])
        delete_lot = reverse("catalog_lot_delete", args=[lot.pk])
        self.client.post(delete_bidder)
        self.client.post(delete_lot)
        self.assertTrue(self.event.bidders.filter(pk=self.buyer.pk).exists())
        self.assertTrue(self.event.catalog_lots.filter(pk=lot.pk).exists())
        delete_sale = reverse("sale_delete", args=[self.event.sales.get().pk])
        self.assertEqual(self.client.get(delete_sale).status_code, 200)
        self.assertTrue(self.event.sales.exists())
        self.assertRedirects(self.client.post(delete_sale), self.workspace)
        self.assertContains(self.client.get(self.catalog), "Available")
        self.assertRedirects(self.client.post(delete_lot), self.catalog)
        self.assertRedirects(self.client.post(delete_bidder), self.workspace)

    def test_exports_include_totals_and_lot_status(self):
        CatalogLot.objects.create(event=self.event, number=12, description="Lamp")
        CatalogLot.objects.create(event=self.event, number=13, description="Bench")
        self.assertRedirects(self.record(), self.workspace)
        Sale.objects.create(event=self.other, lot=12, description="Other sale", amount="8.00")
        response = self.client.get(reverse("export_csv", args=[self.event.pk]))
        rows = list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["Total"], rows[0]["Bidder Name"]), ("25.10", "Ann Smith"))
        self.assertNotIn("Payment", rows[0])
        response = self.client.get(reverse("export_xlsx", args=[self.event.pk]))
        with BytesIO(response.content) as file:
            book = load_workbook(file)
            self.assertEqual(book.sheetnames, ["Sales", "Sales with names", "Bidders", "Lots", "7"])
            self.assertEqual(book["Sales"]["E2"].value, 25.10)
            self.assertEqual(book["7"]["D3"].value, 25.10)
            self.assertEqual([book["Lots"][f"D{i}"].value for i in (2, 3)], ["Sold", "Available"])

    def test_edit_forms_can_infer_event_from_instance(self):
        lot = CatalogLot.objects.create(event=self.event, number=3, description="Vase")
        self.assertRedirects(self.record(), self.workspace)
        self.assertEqual(BidderForm(instance=self.buyer).event, self.event)
        self.assertEqual(CatalogLotForm(instance=lot).event, self.event)
        self.assertEqual(SaleForm(instance=self.event.sales.get()).event, self.event)

    def test_export_keeps_formula_like_descriptions_as_text(self):
        self.assertRedirects(self.record(description="=1+1"), self.workspace)
        response = self.client.get(reverse("export_csv", args=[self.event.pk]))
        row = next(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(row["Description"], "'=1+1")
        response = self.client.get(reverse("export_xlsx", args=[self.event.pk]))
        with BytesIO(response.content) as file:
            cell = load_workbook(file)["Sales"]["A2"]
            self.assertEqual((cell.value, cell.data_type), ("=1+1", "s"))


class EventDeletionTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(title="Auction to delete")
        self.other = Event.objects.create(title="Keep me")
        self.bidder = Bidder.objects.create(
            event=self.event, number=4, name="Buyer"
        )
        self.lot = CatalogLot.objects.create(
            event=self.event, number=4, description="Lamp"
        )
        self.sale = Sale.objects.create(
            event=self.event,
            lot=4,
            description="Lamp",
            amount="10.00",
            bidder=self.bidder,
        )
        self.other_bidder = Bidder.objects.create(
            event=self.other, number=4, name="Other buyer"
        )
        self.other_lot = CatalogLot.objects.create(
            event=self.other, number=4, description="Chair"
        )
        self.other_sale = Sale.objects.create(
            event=self.other,
            lot=4,
            description="Chair",
            amount="5.00",
            bidder=self.other_bidder,
        )
        self.delete_url = reverse("event_delete", args=[self.event.pk])

    def test_delete_links_are_visible(self):
        listing = self.client.get(reverse("event_list"))
        self.assertContains(listing, self.delete_url)
        self.assertContains(listing, ">Delete</a>")

        workspace = self.client.get(
            reverse("event_detail", args=[self.event.pk])
        )
        self.assertContains(workspace, self.delete_url)
        self.assertContains(workspace, "Delete sale")

    def test_confirmation_page_is_safe_and_can_cancel(self):
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auction to delete")
        self.assertContains(
            response, "recorded sales, bidders, and pre-loaded lots"
        )
        self.assertContains(
            response, reverse("event_detail", args=[self.event.pk])
        )
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())
        self.assertEqual(
            self.client.get(reverse("event_detail", args=[self.event.pk])).status_code,
            200,
        )

    def test_post_deletes_only_target_event_and_all_related_records(self):
        response = self.client.post(self.delete_url)
        self.assertRedirects(
            response, reverse("event_list"), fetch_redirect_response=False
        )

        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())
        self.assertFalse(Bidder.objects.filter(event=self.event).exists())
        self.assertFalse(CatalogLot.objects.filter(event=self.event).exists())
        self.assertFalse(Sale.objects.filter(event=self.event).exists())

        self.assertTrue(Event.objects.filter(pk=self.other.pk).exists())
        self.assertTrue(Bidder.objects.filter(pk=self.other_bidder.pk).exists())
        self.assertTrue(CatalogLot.objects.filter(pk=self.other_lot.pk).exists())
        self.assertTrue(Sale.objects.filter(pk=self.other_sale.pk).exists())

        for name, args in [
            ("event_detail", [self.event.pk]),
            ("event_edit", [self.event.pk]),
            ("catalog_lots", [self.event.pk]),
            ("checkout_all", [self.event.pk]),
            ("export_csv", [self.event.pk]),
            ("export_xlsx", [self.event.pk]),
        ]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 404)

        listing = self.client.get(reverse("event_list"))
        self.assertContains(listing, "deleted")
        self.assertNotContains(
            listing, reverse("event_detail", args=[self.event.pk])
        )
        self.assertContains(listing, "Keep me")

    def test_repeated_delete_is_not_found(self):
        self.assertRedirects(self.client.post(self.delete_url), reverse("event_list"))
        self.assertEqual(self.client.get(self.delete_url).status_code, 404)
        self.assertEqual(self.client.post(self.delete_url).status_code, 404)
