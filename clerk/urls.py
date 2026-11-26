from django.urls import path

from . import views

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("events/new/", views.event_form, name="event_new"),
    path("events/<int:pk>/", views.event_detail, name="event_detail"),
    path("events/<int:pk>/lots/", views.catalog_lots, name="catalog_lots"),
    path("events/<int:pk>/edit/", views.event_form, name="event_edit"),
    path("events/<int:pk>/delete/", views.event_delete, name="event_delete"),
    path("sales/<int:pk>/edit/", views.sale_form, name="sale_edit"),
    path("sales/<int:pk>/delete/", views.sale_delete, name="sale_delete"),
    path("bidders/<int:pk>/edit/", views.bidder_form, name="bidder_edit"),
    path("bidders/<int:pk>/delete/", views.bidder_delete, name="bidder_delete"),
    path("lots/<int:pk>/edit/", views.catalog_lot_form, name="catalog_lot_edit"),
    path("lots/<int:pk>/delete/", views.catalog_lot_delete, name="catalog_lot_delete"),
    path("events/<int:pk>/checkout/", views.checkout_all, name="checkout_all"),
    path(
        "events/<int:pk>/checkout/<int:bidder_pk>/",
        views.checkout_bidder,
        name="checkout_bidder",
    ),
    path("events/<int:pk>/export.csv", views.download_csv, name="export_csv"),
    path("events/<int:pk>/export.xlsx", views.download_xlsx, name="export_xlsx"),
]
