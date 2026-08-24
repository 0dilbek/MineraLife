# clients/urls.py
from django.urls import path
from .views import (
    ClientCreateView,
    ClientDeleteView,
    ClientDetailView,
    ClientListView,
    ClientUpdateView,
    check_name_exists,
    clients_map,
    toggle_client_departed,
    DebtorListView,
    DebtorDetailView,
    close_client_debt,
)

app_name = 'clients'
urlpatterns = [
    path('', ClientListView.as_view(), name='list'),
    path('debtors/', DebtorListView.as_view(), name='debtors'),
    path('debtors/<int:pk>/', DebtorDetailView.as_view(), name='debtor_detail'),
    path(
        'debtors/<int:client_pk>/orders/<int:order_pk>/close/',
        close_client_debt,
        name='close_debt',
    ),
    path("create/", ClientCreateView.as_view(), name="create"), 
    path('map/', clients_map, name='map'),
    path("<int:pk>/", ClientDetailView.as_view(), name="detail"),
    path("<int:pk>/toggle-departed/", toggle_client_departed, name="toggle_departed"),
    path("<int:pk>/delete/", ClientDeleteView.as_view(), name="delete"),
    path("<int:pk>/update/", ClientUpdateView.as_view(), name="update"),
    path('check-name/', check_name_exists, name='check_name'),
]
