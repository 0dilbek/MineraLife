from . import  views
from django.urls import path
from .views import (
    CourierListView, CourierDetailView, CourierCreateView,
    CourierUpdateView, CourierPasswordUpdateView, CourierDeleteView, courier_dashboard,
    courier_debtors,
)

app_name = "couriers"

urlpatterns = [
    path("", CourierListView.as_view(), name="list"),
    path("dashboard/", courier_dashboard, name="dashboard"),
    path("debtors/", courier_debtors, name="debtors"),
    path("create/", CourierCreateView.as_view(), name="create"),
    path("<int:pk>/", CourierDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", CourierUpdateView.as_view(), name="update"),
    path("<int:pk>/password/", CourierPasswordUpdateView.as_view(), name="password"),
    path("<int:pk>/delete/", CourierDeleteView.as_view(), name="delete"),
    path("dashboard/", views.courier_dashboard, name="dashboard"),
    path("order/<int:pk>/update/", views.courier_order_update, name="order_update"),
    path("map/", views.courier_map, name="map"),  # xarita uchun view keyin yozamiz
    path("location/update/", views.courier_update_location, name="update_location"),
    path("live-locations/", views.courier_live_locations, name="live_locations"),
]
