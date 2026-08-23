from django.urls import path
from . import views
from .mobile_views import (
    MobileDashboardView,
    MobileLocationView,
    MobileLoginView,
    MobileLogoutView,
    MobileMeView,
    MobileOrderDetailView,
    MobileOrderListView,
)

app_name = 'api'

urlpatterns = [
    path('mobile/v1/auth/login/', MobileLoginView.as_view(), name='mobile_login'),
    path('mobile/v1/auth/logout/', MobileLogoutView.as_view(), name='mobile_logout'),
    path('mobile/v1/me/', MobileMeView.as_view(), name='mobile_me'),
    path('mobile/v1/dashboard/', MobileDashboardView.as_view(), name='mobile_dashboard'),
    path('mobile/v1/orders/', MobileOrderListView.as_view(), name='mobile_orders'),
    path('mobile/v1/orders/<int:order_id>/', MobileOrderDetailView.as_view(), name='mobile_order_detail'),
    path('mobile/v1/location/', MobileLocationView.as_view(), name='mobile_location'),

    # Client nomi bo'yicha qidirish
    path('orders/client/', views.get_client_orders, name='client_orders'),
    
    # Client ID bo'yicha
    path('orders/client/<int:client_id>/', views.get_client_orders_by_id, name='client_orders_by_id'),
]
