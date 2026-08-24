from django.urls import path
from .views import (
    OrderDeleteView, OrderListView, OrderCreateView, OrderDetailView, OrderUpdateView, OrdersMapView, 
    assign_courier_to_order, bulk_assign_courier_to_orders, save_courier_route, delete_courier_route,
    mark_order_as_debt,
)

app_name = "orders"

urlpatterns = [
    path("", OrderListView.as_view(), name="list"),
    path("create/", OrderCreateView.as_view(), name="create"),
    path("map/", OrdersMapView.as_view(), name="map"),
    path("<int:pk>/", OrderDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", OrderUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", OrderDeleteView.as_view(), name="delete"),
    path("<int:order_id>/mark-debt/", mark_order_as_debt, name="mark_debt"),
    path("<int:order_id>/assign-courier/", assign_courier_to_order, name="assign_courier"),
    path("bulk-assign-courier/", bulk_assign_courier_to_orders, name="bulk_assign_courier"),
    path("route/save/", save_courier_route, name="save_route"),
    path("route/delete/", delete_courier_route, name="delete_route"),
]
