from django.urls import path
from .views import reports_view, export_excel, client_history_view

app_name = "hisobotlar"

urlpatterns = [
    path("", reports_view, name="reports"),
    path("clients/<int:client_id>/", client_history_view, name="client_history"),
    path("export-excel/", export_excel, name="export_excel"),
]
