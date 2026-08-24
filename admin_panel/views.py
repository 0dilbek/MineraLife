import json

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from orders.models import Order


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
        "status_raw": "completed" if o.is_debt else o.status,
        "is_debt": o.is_debt,
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
    today, points, counts = _today_order_points()
    context = {
        "today": today,
        "points": json.dumps(points),
        "order_counts": counts,
        "yandex_maps_api_key": settings.YANDEX_MAPS_API_KEY,
    }

    return render(request, "admin_welcome.html", context)


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
