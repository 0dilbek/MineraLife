"""
URL configuration for admin_panel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import admin_welcome, admin_today_map_data, dashboard_redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('products/', include('products.urls'), name='products'),
    path('clients/', include('clients.urls'), name='clients'),
    path('orders/', include('orders.urls'), name='orders'),
    path('couriers/', include('couriers.urls'), name='couriers'),
    path('accounts/', include('django.contrib.auth.urls')),  # login/logout/password_*
    path('dashboard/admin/', admin_welcome, name='admin_welcome'),
    path('dashboard/admin/today-map-data/', admin_today_map_data, name='admin_today_map_data'),
    path("reports/", include("hisobotlar.urls")),
    path('', dashboard_redirect, name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
