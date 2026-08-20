import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from clients.models import Client
from couriers.models import CourierLocation
from orders.models import Order
from products.models import Product


ADMIN_UI_SESSION_KEY = "admin_ui_mode"
ADMIN_UI_MODES = {"classic", "modern"}


def _today_order_points():
    today = timezone.localdate()
    qs = (Order.objects
          .select_related("client", "courier")
          .filter(
              effective_date=today,
              client__latitude__isnull=False,
              client__longitude__isnull=False,
          )
          .order_by("-created_at"))

    points = [{
        "id": o.id,
        "client": o.client.name,
        "lat": o.client.latitude,
        "lon": o.client.longitude,
        "status": o.get_status_display(),
        "status_raw": o.status,
        "courier": (o.courier.username if o.courier_id else None),
        "courier_id": o.courier_id,
        "outquantity": o.outquantity,
    } for o in qs]

    counts = {
        "total": qs.count(),
        "pending": qs.filter(status="pending").count(),
        "completed": qs.filter(status="completed").count(),
        "cancelled": qs.filter(status="cancelled").count(),
    }
    return today, points, counts


@user_passes_test(lambda u: u.is_superuser)
def admin_welcome(request):
    if request.GET.get("choose") == "1" or request.session.get(ADMIN_UI_SESSION_KEY) not in ADMIN_UI_MODES:
        return render(request, "admin_ui_choice.html")

    today, points, counts = _today_order_points()
    context = {
        "today": today,
        "points": json.dumps(points),
        "order_counts": counts,
        "yandex_maps_api_key": settings.YANDEX_MAPS_API_KEY,
    }

    if request.session[ADMIN_UI_SESSION_KEY] == "modern":
        today_orders = Order.objects.filter(effective_date=today)
        completed = today_orders.filter(status="completed")
        payments = completed.aggregate(
            cash=Sum("cash_amount"),
            card=Sum("card_amount"),
            transfer=Sum("perechesleniya_amount"),
            debt=Sum("debt_amount"),
            delivered=Sum("outquantity"),
        )
        paid_total = sum((payments[key] or 0) for key in ("cash", "card", "transfer"))
        online_cutoff = timezone.now() - timedelta(minutes=10)
        courier_count = User.objects.filter(groups__name="couriers", is_active=True).distinct().count()

        context.update({
            "paid_total": paid_total,
            "debt_total": payments["debt"] or 0,
            "delivered_total": payments["delivered"] or 0,
            "unassigned_count": today_orders.filter(courier__isnull=True).exclude(status="cancelled").count(),
            "completion_percent": round((counts["completed"] / counts["total"] * 100) if counts["total"] else 0),
            "client_count": Client.objects.count(),
            "product_count": Product.objects.count(),
            "courier_count": courier_count,
            "online_courier_count": CourierLocation.objects.filter(updated_at__gte=online_cutoff).count(),
            "recent_orders": today_orders.select_related("client", "courier").order_by("-created_at")[:7],
        })
        return render(request, "admin_welcome_modern.html", context)

    return render(request, "admin_welcome.html", context)


@require_POST
@user_passes_test(lambda u: u.is_superuser)
def set_admin_ui(request):
    mode = request.POST.get("mode")
    if mode not in ADMIN_UI_MODES:
        return JsonResponse({"success": False, "error": "Noma'lum interfeys turi"}, status=400)

    request.session[ADMIN_UI_SESSION_KEY] = mode
    requested_next = request.POST.get("next") or reverse("admin_welcome")
    if not url_has_allowed_host_and_scheme(
        requested_next,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        requested_next = reverse("admin_welcome")
    return redirect(requested_next)


@user_passes_test(lambda u: u.is_superuser)
def admin_today_map_data(request):
    """Admin dashboard xaritasini davriy yangilash uchun JSON"""
    today, points, counts = _today_order_points()
    return JsonResponse({
        "date": today.isoformat(),
        "points": points,
        "counts": counts,
    })


@login_required
def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('admin_welcome')   # admin uchun
    else:
        return redirect('couriers:dashboard')  # kuryer uchun
