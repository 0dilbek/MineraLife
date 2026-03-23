from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Client nomi bo'yicha qidirish
    path('orders/client/', views.get_client_orders, name='client_orders'),
    
    # Client ID bo'yicha
    path('orders/client/<int:client_id>/', views.get_client_orders_by_id, name='client_orders_by_id'),
]
